# Fabric setup guide (Phase 0 and Phase 1)

Click-by-click steps, checked against Microsoft Learn on 2026-11-10. Menu labels are in **bold**,
exactly as the docs write them. If the portal shows something different, stop and note it here.
Names of items and tables come from `config/sources.json`.

Sources: [Create a workspace](https://learn.microsoft.com/en-us/fabric/fundamentals/create-workspaces),
[Runtime 2.0](https://learn.microsoft.com/en-us/fabric/data-engineering/runtime-2-0),
[Create a lakehouse](https://learn.microsoft.com/en-us/fabric/data-engineering/create-lakehouse),
[Create a warehouse](https://learn.microsoft.com/en-us/fabric/data-warehouse/create-warehouse),
[Git get started](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/git-get-started),
[Lookup](https://learn.microsoft.com/en-us/fabric/data-factory/lookup-activity),
[ForEach](https://learn.microsoft.com/en-us/fabric/data-factory/foreach-activity),
[HTTP copy](https://learn.microsoft.com/en-us/fabric/data-factory/connector-http-copy-activity),
[Lakehouse copy](https://learn.microsoft.com/en-us/fabric/data-factory/connector-lakehouse-copy-activity),
[Activity general settings](https://learn.microsoft.com/en-us/fabric/data-factory/activity-overview),
[Dataflow Gen2 CI/CD](https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-gen2-cicd-and-git-integration),
[Dataflow public parameters](https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-parameters),
[Dataflow destinations](https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-gen2-data-destinations-and-managed-settings),
[Dataflow activity](https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-activity),
[NotebookUtils credentials](https://learn.microsoft.com/en-us/fabric/data-engineering/notebookutils/notebookutils-credentials).

---

## Phase 0: workspace, storage, Git

### 0.1 F2 capacity (Azure portal)

1. Azure portal → search **Microsoft Fabric** → **Create**.
2. Choose a resource group, a capacity name (lowercase letters and digits), the region closest to you, size **F2**,
   and your account as capacity administrator → **Review + create** → **Create**.
3. ⚠️ The capacity bills while it runs. **At the end of every working session, open the capacity in the
   Azure portal and select Pause**, then select **Resume** when you start again.

### 0.2 Tenant settings (once)

Fabric → gear icon → **Admin portal** → **Tenant settings** (the docs also give the path
**OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**). Enable:

- **Users can create Fabric items**
- **Users can synchronize workspace items with their Git repositories**
- **Users can synchronize workspace items with GitHub repositories**

### 0.3 Workspace on the F2 capacity

1. Nav pane → **Workspaces** → **New workspace**.
2. Name: `fabric-nyc-analytics`. Expand **Advanced** → **Workspace type**: choose the Fabric capacity type
   and select your F2 capacity → **Apply**.
3. Check it: workspace → **Workspace settings** → **Workspace type** shows the F2 capacity.

### 0.4 Runtime 2.0

**Workspace settings** → **Data Engineering/Science** → **Spark settings** → **Environment** tab →
**Runtime version** → **2.0 (Spark 4.1, Delta 4.2)** → **Save**. Record it in README (Fabric runtime section).

### 0.5 Lakehouses and Warehouse

Choice: **two lakehouses (`lh_bronze`, `lh_silver`) plus one Warehouse (`wh_gold`)**. One item per
layer makes the medallion boundaries visible, permissions can be set per layer, and the Gold layer
uses Warehouse T-SQL as required. A single lakehouse with schemas would also work, but it hides the
layer boundary inside one item.

For each lakehouse: workspace → **+ New item** → **Lakehouse** → name `lh_bronze` (then `lh_silver`) →
**clear the Lakehouse schemas checkbox** → **Create**.
*Why clear it:* with schemas on, Dataflow destinations need the extra connection option
**Navigate using full hierarchy**, and that option has a fast-copy limitation. Without schemas,
tables are still addressed as `lh_silver.dbo.<table>` from the Warehouse.

Warehouse: **+ New item** → **Warehouse** (under **Store data**) → name `wh_gold` → **Create**.

### 0.6 Connect the workspace to GitHub

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** →
   **Generate new token**: repository access *Only select repositories* → `fabric-nyc-analytics`;
   permissions → **Contents: Read and write**. Copy the token (it is shown only once). Do not save it in any file.
2. Fabric workspace → **Workspace settings** → **Git integration** → **GitHub** → **Add account**:
   *Display name* any; *Personal access token* the token; *Repository URL*
   `https://github.com/azizbekb/fabric-nyc-analytics` → **Connect**.
3. Branch `main`, Folder **`fabric`** → **Connect and sync**. The Git folder has no items yet, so the
   workspace items (two lakehouses and the warehouse) are written to `fabric/`.
4. Tell me, and I run `git pull` to inspect the real item folder format before editing anything.

Daily loop after that:
- Change in Fabric → **Source control** icon → **Changes** → select → **Commit**.
- Change pushed from the repo → **Source control** → **Updates** → **Update all** → **Update**.
- ⚠️ After **Update all**, a Dataflow must be **opened and saved once** in the editor, otherwise the
  next refresh does not use the new version (documented limitation).

Lakehouse **data** (files and tables) is not stored in Git. Only the item definitions are.

---

## Phase 1: ingestion

### 1.1 Secret: OpenAQ key in Azure Key Vault

Constraint: OpenAQ accepts the key only as the `X-API-Key` header. Fabric's "Web API" key credential
sends the key as a URL query parameter, which OpenAQ rejects with 401, so a stored connection
credential cannot carry it. Chosen design (the key never appears in Git or in run logs):

```
Key Vault secret ──getSecret──▶ notebook nb_get_openaq_key (Secure output)
                 ──exitValue──▶ Dataflow df_openaq, required public parameter OpenAQApiKey (Secure input)
```

1. Azure portal → **Create a resource** → **Key Vault** → same resource group, a globally unique name,
   permission model **Azure role-based access control** → **Create**.
2. Key Vault → **Access control (IAM)** → **Add role assignment** → **Key Vault Secrets Officer** → your user.
3. Key Vault → **Objects** → **Secrets** → **Generate/Import** → name `openaq-api-key`, value = your key.
4. Send me the vault URL (`https://<name>.vault.azure.net/`). I add it to `config/sources.json`.
   The vault URL is not a secret.

Trade-off: one extra short notebook run per pipeline run. Simpler options were rejected: a parameter
default would be stored in Git, and a value typed by hand cannot run on a daily schedule.

### 1.2 Pipeline `pl_ingest`

Workspace → **+ New item** → **Pipeline** → name `pl_ingest`. Below, `cfg` stands for
`activity('Lookup config').output.firstRow`.

Two HTTP connections (create them in the first Copy activity via **Connection** → **New** →
**HTTP**, Authentication **Anonymous**):
- `http_github_raw`, URL `https://raw.githubusercontent.com` (= `repo.raw_base_url`)
- `http_tlc`, URL `https://d37ci6vzurychx.cloudfront.net` (= `taxi.base_url`)

A connection's URL is fixed when it is created, so these two URLs exist both in config and in the
connection. That is a platform limitation, documented here.

| # | Activity (Name) | Settings |
|---|---|---|
| 1 | **Copy data** `Copy config` | Source: `http_github_raw`, **Relative URL** `azizbekb/fabric-nyc-analytics/main/config/sources.json`, file format **Binary**. Destination: `lh_bronze`, **Root folder** **Files**, **File path** `config` / `sources.json`, **Binary**. This path is the only bootstrap literal: the config cannot point to itself before it is read. |
| 2 | **Lookup** `Lookup config` | **Connection** `lh_bronze`, root **Files**, file `config/sources.json`, format **JSON**, **First row only** ✓ (the file is one JSON object). Use **Preview data** to check. |
| 3 | **ForEach** `ForEach taxi month` | **Items**: `@activity('Lookup config').output.firstRow.taxi.months`. **Sequential** off, **Batch count** 2 (small F2). |
| 3a | inside: **Copy data** `Copy taxi month` | Source `http_tlc`, **Relative URL** `@replace(activity('Lookup config').output.firstRow.taxi.path_template, '{month}', item())`, **Binary**. Destination `lh_bronze` **Files**, folder `@activity('Lookup config').output.firstRow.taxi.bronze_folder`, file name `@last(split(replace(activity('Lookup config').output.firstRow.taxi.path_template, '{month}', item()), '/'))`, **Binary**. |
| 4 | **Copy data** `Copy taxi zones` | Source `http_tlc`, Relative URL `@activity('Lookup config').output.firstRow.taxi_zones.path`; destination folder `…taxi_zones.bronze_folder`, file name `@last(split(activity('Lookup config').output.firstRow.taxi_zones.path, '/'))`, Binary. |
| 5 | **Copy data** `Copy monitor zones` | Source `http_github_raw`, Relative URL `@concat(activity('Lookup config').output.firstRow.repo.raw_path, '/', activity('Lookup config').output.firstRow.monitor_zones.path)`; destination folder `…monitor_zones.bronze_folder`, Binary. |
| 6 | **Notebook** `Get OpenAQ key` | Notebook `nb_get_openaq_key` (I write it in Phase 1). **General** → advanced → **Secure output** ✓. |
| 7 | **Dataflow** `Run df_openaq` | After 6. Dataflow `df_openaq`; **Dataflow parameters**: `OpenAQApiKey` = `@activity('Get OpenAQ key').output.result.exitValue`. **Secure input** ✓. |
| 8 | **Dataflow** `Run df_worldbank`, `Run df_ecb` | No parameters. |

Connect 1 → 2 → (3, 4, 5, 6, 8) with **On success** arrows, and 6 → 7. **Save**, then **Run**.
Check the **Output** tab below the canvas.

Ingestion metadata for files: Bronze files stay byte-for-byte unchanged. The source and month are in
the folder and file name. The Silver notebook adds `source_file` and `load_ts` from Spark's file
metadata (`_metadata.file_path`, `_metadata.file_modification_time`).

### 1.3 Dataflows Gen2

For each dataflow: workspace → **Create new item** → **Dataflow Gen2** → name → **Create**
(Git support is on by default). Home → **Get data** → **Blank query** → **Advanced editor** →
paste the M code below → **OK**.

Shared parameter (Home → **Manage parameters** → **New**): `ConfigUrl`, type Text, current value
`https://raw.githubusercontent.com/azizbekb/fabric-nyc-analytics/main/config/sources.json`.

Destination for each query: select the query → **Add data destination** (top ribbon) →
**Lakehouse** → `lh_bronze` → **New table** named as in config (`openaq.bronze_table`, …) →
keep **Use automatic settings** (update method **Replace**). The table name has to be typed in the
UI, because destination paths cannot be parameterized (documented limitation). It must match config.

Lakehouse destinations do **not** support `DateTimeZone`, so `load_ts` is a UTC `datetime`.

Rate limits: `df_openaq` makes 1 + (number of sensors) requests, about 35 today, under the
60 requests/minute limit.

If saving fails with a *dynamic data source* error, replace `Cfg[base_url]` in `Web.Contents` with
the literal base URL, keep the path in `RelativePath`, and note it here.

#### `df_openaq` → `bronze_openaq_measurements`

Extra parameter: `OpenAQApiKey`, type Text, **Required**, current value `set-at-runtime`
(a placeholder: Git stores only this word). Then Home → **Options** → *dataflow* → **Parameters** →
**Enable parameters to be discovered and override for execution** → **OK**.

```m
let
    Config = Json.Document(Web.Contents(ConfigUrl)),
    Cfg = Config[openaq],
    Months = List.Sort(Config[taxi][months]),
    DateFrom = List.First(Months) & "-01",
    DateTo = Date.ToText(Date.EndOfMonth(Date.FromText(List.Last(Months) & "-01")), [Format = "yyyy-MM-dd"]),
    Num = (n as number) as text => Number.ToText(n, "G", "en-US"),
    Field = (r as nullable record, name as text) => if r = null then null else Record.FieldOrDefault(r, name),
    GetPage = (path as text, query as record, page as number) as list =>
        Json.Document(Web.Contents(Cfg[base_url], [
            RelativePath = path,
            Query = query & [limit = Num(Cfg[page_limit]), page = Num(page)],
            Headers = [#"X-API-Key" = OpenAQApiKey]
        ]))[results],
    GetAll = (path as text, query as record) as list =>
        List.Combine(List.Generate(
            () => [page = 1, rows = GetPage(path, query, 1)],
            each [rows] <> null,
            each [page = [page] + 1,
                  rows = if List.Count([rows]) < Cfg[page_limit] then null else GetPage(path, query, [page] + 1)],
            each [rows])),
    Locations = GetAll(Cfg[locations_path], [
        coordinates = Num(Cfg[center][lat]) & "," & Num(Cfg[center][lon]),
        radius = Num(Cfg[radius_m])]),
    Selected = List.Select(Locations, each [isMonitor] or not Cfg[monitors_only]),
    Sensors = List.Combine(List.Transform(Selected, (loc) =>
        List.Transform(
            List.Select(loc[sensors], (s) => List.Contains(Cfg[parameters], s[parameter][name])),
            (s) => [location_id = loc[id], location_name = loc[name], sensor_id = s[id],
                    parameter = s[parameter][name], units = s[parameter][units]]))),
    Days = List.Combine(List.Transform(Sensors, (s) =>
        List.Transform(
            GetAll(Text.Replace(Cfg[daily_path], "{sensor_id}", Num(s[sensor_id])), [date_from = DateFrom, date_to = DateTo]),
            (d) => s & [
                period_start_local = d[period][datetimeFrom][local],
                value = d[value],
                value_min = Field(d[summary], "min"),
                value_max = Field(d[summary], "max"),
                percent_complete = Field(d[coverage], "percentComplete"),
                has_source_flags = Field(d[flagInfo], "hasFlags")]))),
    Result = Table.FromRecords(Days, type table [
        location_id = Int64.Type, location_name = text, sensor_id = Int64.Type, parameter = text, units = text,
        period_start_local = text, value = nullable number, value_min = nullable number, value_max = nullable number,
        percent_complete = nullable number, has_source_flags = nullable logical]),
    WithSource = Table.AddColumn(Result, "source", each "openaq", type text),
    WithLoadTs = Table.AddColumn(WithSource, "load_ts", each DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow()), type datetime)
in
    WithLoadTs
```

Notes: `Num` formats numbers with `en-US`, so 40.7128 never becomes "40,7128". The paging stops
when a page is shorter than `limit`, because `meta.found` can be the text `">1000"`.

#### `df_worldbank` → `bronze_worldbank_gdp`

```m
let
    Cfg = Json.Document(Web.Contents(ConfigUrl))[worldbank],
    GetPage = (page as number) => Json.Document(Web.Contents(Cfg[base_url], [
        RelativePath = Cfg[path],
        Query = Cfg[query] & [per_page = Text.From(Cfg[per_page]), page = Text.From(page)]])),
    Pages = GetPage(1){0}[pages],
    Rows = List.Combine(List.Transform({1..Pages}, each GetPage(_){1})),
    Records = List.Transform(Rows, each [
        country_code = [countryiso3code], indicator_id = [indicator][id], year = [date], value = [value]]),
    Result = Table.FromRecords(Records, type table [
        country_code = text, indicator_id = text, year = text, value = nullable number]),
    WithSource = Table.AddColumn(Result, "source", each "worldbank", type text),
    WithLoadTs = Table.AddColumn(WithSource, "load_ts", each DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow()), type datetime)
in
    WithLoadTs
```

#### `df_ecb` → `bronze_ecb_fx`

All CSV columns are kept unchanged, as text (Bronze = raw).

```m
let
    Cfg = Json.Document(Web.Contents(ConfigUrl))[ecb],
    Raw = Csv.Document(
        Web.Contents(Cfg[base_url], [RelativePath = Cfg[path], Query = Cfg[query]]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Raw, [PromoteAllScalars = true]),
    AsText = Table.TransformColumnTypes(Promoted, List.Transform(Table.ColumnNames(Promoted), each {_, type nullable text})),
    WithSource = Table.AddColumn(AsText, "source", each "ecb", type text),
    WithLoadTs = Table.AddColumn(WithSource, "load_ts", each DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow()), type datetime)
in
    WithLoadTs
```

After each dataflow: **Save and run**, check the table in `lh_bronze`, then **Source control** →
**Commit**. I then `git pull` and replace these drafts with a pointer to the real
`fabric/<name>.Dataflow/` item files, so the M code has one home only.

### 1.4 First checks

- `lh_bronze` → **Files**: `config/sources.json`, `taxi/yellow_tripdata_2024-0[1-6].parquet`,
  `taxi_zones/taxi_zone_lookup.csv`, `reference/monitor_zones.csv`.
- `lh_bronze` → **Tables**: the three `bronze_*` tables, row counts close to `docs/sources.md`
  (OpenAQ ≈ 24 sensors × ~180 days; GDP 66 rows; ECB ~7,200 rows).
- **Pause the F2 capacity** when you finish.

---

## Phase 3: Gold (Warehouse)

Sources: [T-SQL surface area](https://learn.microsoft.com/en-us/fabric/data-warehouse/tsql-surface-area),
[Data types](https://learn.microsoft.com/en-us/fabric/data-warehouse/data-types),
[Table constraints](https://learn.microsoft.com/en-us/fabric/data-warehouse/table-constraints),
[Warehouse Git integration](https://learn.microsoft.com/en-us/fabric/data-warehouse/git-integration),
[Cross-database queries](https://learn.microsoft.com/en-us/fabric/data-warehouse/query-warehouse),
[GENERATE_SERIES](https://learn.microsoft.com/en-us/sql/t-sql/functions/generate-series-transact-sql?view=fabric),
[Stored procedure activity](https://learn.microsoft.com/en-us/fabric/data-factory/stored-procedure-activity).

### 3.1 Create the objects

1. Open `wh_gold` → **New SQL query** → paste `drafts/warehouse/gold_ddl.sql` → **Run**.
2. **New SQL query** → paste `drafts/warehouse/gold_load.sql` → **Run** (it creates the procedures).
3. Explorer → **+ Warehouses** → add `lh_silver`, so its tables are visible next to Gold.
   Queries use three-part names: `lh_silver.dbo.silver_taxi_trips`.
4. Test: `EXEC dbo.load_dim_date;` then `SELECT TOP 100 * FROM dbo.DimDate;`.
5. **Source control** → **Commit**. The Warehouse is saved as a database project (one `.sql` file per
   object). I then move these drafts into the item folder and delete `drafts/warehouse/`.

### 3.2 Load step in the pipeline

1. **Refresh SQL analytics endpoint** activity for `lh_silver`, so the Warehouse reads the Delta
   tables the notebooks just wrote.
2. **ForEach** `ForEach gold procedure`: **Items** `@activity('Lookup config').output.firstRow.gold.load_procedures`,
   **Sequential** ✓ (dimensions first, because `load_dim_fx` reads `DimDate`).
   Inside it: **Stored procedure** activity, connection `wh_gold`, procedure name (dynamic content) `@concat('dbo.', item())`.

### Known risk and fallback

The docs say *cross-item dependencies between warehouses and SQL analytics endpoints aren't
currently supported in development workflows*. Our procedures read `lh_silver`. If the Warehouse
**Commit** or **Update all** fails for that reason, keep the tables in the Warehouse project and run the
load SQL from a pipeline **Script** activity instead (same statements). Note the result here.

Fabric T-SQL rules applied: `varchar` not `nvarchar`, `date`/`datetime2` not `datetime`,
`smallint` not `tinyint`; keys only via `ALTER TABLE … NONCLUSTERED … NOT ENFORCED`;
no default constraints, triggers, recursive CTEs or system-table queries (DimDate uses `GENERATE_SERIES`).
