let
    Lakehouse = Lakehouse.Contents([HierarchicalNavigation = null, EnableVorder = true, OutputMetadataRefresh = true]),
    Workspace = Lakehouse{[workspaceId = "6e107ded-9300-4274-a3af-9ca212441d27"]}[Data],
    Bronze = Workspace{[lakehouseId = "d09c7e6f-8019-4094-b646-005b9957c284"]}[Data],
    Files = Bronze{[Id = "Files", ItemKind = "Folder"]}[Data],
    KeyFile = Files{[Name = "secrets"]}[Content]{[Name = "openaq_api_key.txt"]}[Content],
    ApiKey = Text.Trim(Text.FromBinary(KeyFile)),
    Config = Json.Document(Web.Contents(ConfigUrl)),
    Cfg = Config[openaq],
    Months = List.Sort(Config[taxi][months]),
    DateFrom = List.First(Months) & "-01",
    LastDay = Date.EndOfMonth(Date.FromText(List.Last(Months) & "-01")),
    DateTo = Date.ToText(LastDay, [Format = "yyyy-MM-dd"]),
    Num = (n as number) as text => Number.ToText(n, "G", "en-US"),
    Field = (r as nullable record, name as text) =>
        if r = null then null else Record.FieldOrDefault(r, name),
    GetPage = (path as text, query as record, page as number) as list =>
        let
            Options = [
                RelativePath = path,
                Query = query & [limit = Num(Cfg[page_limit]), page = Num(page)],
                Headers = [#"X-API-Key" = ApiKey]]
        in
            Json.Document(Web.Contents(Cfg[base_url], Options))[results],
    GetAll = (path as text, query as record) as list =>
        let
            Start = [page = 1, rows = GetPage(path, query, 1)],
            IsFull = (state as record) as logical => List.Count(state[rows]) >= Cfg[page_limit],
            Next = (state as record) as record => [
                page = state[page] + 1,
                rows = if IsFull(state) then GetPage(path, query, state[page] + 1) else null],
            Pages = List.Generate(
                () => Start,
                (state) => state[rows] <> null,
                Next,
                (state) => state[rows])
        in
            List.Combine(Pages),
    Center = Num(Cfg[center][lat]) & "," & Num(Cfg[center][lon]),
    Locations = GetAll(Cfg[locations_path], [coordinates = Center, radius = Num(Cfg[radius_m])]),
    Selected = List.Select(Locations, (loc) => loc[isMonitor] or not Cfg[monitors_only]),
    ToSensor = (loc as record, s as record) as record => [
        location_id = loc[id],
        location_name = loc[name],
        sensor_id = s[id],
        parameter = s[parameter][name],
        units = s[parameter][units]],
    SensorsOf = (loc as record) as list =>
        List.Transform(
            List.Select(loc[sensors], (s) => List.Contains(Cfg[parameters], s[parameter][name])),
            (s) => ToSensor(loc, s)),
    Sensors = List.Combine(List.Transform(Selected, SensorsOf)),
    ToDay = (s as record, d as record) as record => s & [
        period_start_local = d[period][datetimeFrom][local],
        value = d[value],
        value_min = Field(d[summary], "min"),
        value_max = Field(d[summary], "max"),
        percent_complete = Field(d[coverage], "percentComplete"),
        has_source_flags = Field(d[flagInfo], "hasFlags")],
    DaysOf = (s as record) as list =>
        let
            Path = Text.Replace(Cfg[daily_path], "{sensor_id}", Num(s[sensor_id])),
            Rows = GetAll(Path, [date_from = DateFrom, date_to = DateTo])
        in
            List.Transform(Rows, (d) => ToDay(s, d)),
    Days = List.Combine(List.Transform(Sensors, DaysOf)),
    Result = Table.FromRecords(Days, type table [
        location_id = Int64.Type, location_name = text, sensor_id = Int64.Type,
        parameter = text, units = text, period_start_local = text,
        value = nullable number, value_min = nullable number, value_max = nullable number,
        percent_complete = nullable number, has_source_flags = nullable logical]),
    WithSource = Table.AddColumn(Result, "source", each "openaq", type text),
    WithLoadTs = Table.AddColumn(WithSource, "load_ts",
        each DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow()), type datetime)
in
    WithLoadTs
