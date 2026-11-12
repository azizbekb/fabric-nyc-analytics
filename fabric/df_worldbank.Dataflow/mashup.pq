[DefaultOutputDestinationSettings = [DestinationDefinition = [Kind = "Reference", QueryName = "DefaultDestination", IsNewTarget = true], UpdateMethod = [Kind = "Replace"], DestinationTypeSettings = [Kind = "Table"]], StagingDefinition = [Kind = "FastCopy"]]
section Section1;
[BindToDefaultDestination = true]
shared bronze_worldbank_gdp = let
    Lakehouse = Lakehouse.Contents([HierarchicalNavigation = null, EnableVorder = true, OutputMetadataRefresh = true]),
    Workspace = Lakehouse{[workspaceId = "6e107ded-9300-4274-a3af-9ca212441d27"]}[Data],
    Bronze = Workspace{[lakehouseId = "d09c7e6f-8019-4094-b646-005b9957c284"]}[Data],
    Files = Bronze{[Id = "Files", ItemKind = "Folder"]}[Data],
    ConfigFile = Files{[Name = "config"]}[Content]{[Name = "sources.json"]}[Content],
    Cfg = Json.Document(ConfigFile)[worldbank],
    GetPage = (page as number) => Json.Document(Web.Contents(Cfg[base_url], [
        RelativePath = Cfg[path],
        Query = Cfg[query] & [per_page = Text.From(Cfg[per_page]), page = Text.From(page)]])),
    Pages = GetPage(1){0}[pages],
    Rows = List.Combine(List.Transform({1..Pages}, (p) => GetPage(p){1})),
    Records = List.Transform(Rows, (r) => [
        country_code = r[countryiso3code],
        indicator_id = r[indicator][id],
        year = r[date],
        value = r[value]]),
    Result = Table.FromRecords(Records, type table [
        country_code = text, indicator_id = text, year = text, value = nullable number]),
    WithSource = Table.AddColumn(Result, "source", each "worldbank", type text),
    WithLoadTs = Table.AddColumn(WithSource, "load_ts",
        each DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow()), type datetime)
in
    WithLoadTs;
shared DefaultDestination = let
  Source = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true]),
  Navigation = Source{[workspaceId = "6e107ded-9300-4274-a3af-9ca212441d27"]}[Data],
  #"Navigation 1" = Navigation{[lakehouseId = "d09c7e6f-8019-4094-b646-005b9957c284"]}[Data],
  #"Navigation 2" = #"Navigation 1"{[Id = "dbo", ItemKind = "Schema"]}[Data]
in
  #"Navigation 2";
