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

Status (2026-11-11): **Phase 0 is done (0.1–0.6).** Workspace `nyc-analytics` on the **Fabric Trial** capacity
(region East Asia, ~59 days left), Runtime 2.0 is the workspace default, default environment Off, Starter Pool.

### 0.1 Capacity ✅ (Fabric Trial)

The project runs on the free Fabric Trial capacity, so there is nothing to pause. If a paid F2 capacity is
used later: Azure portal → **Microsoft Fabric** → **Create**, size **F2**, and **Pause** it after every session.

### 0.2 Tenant settings ✅ (done 2026-11-11)

Fabric → gear icon → **Admin portal** → **Tenant settings** (the docs also give the path
**OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**). Enable:

- **Users can create Fabric items**
- **Users can sync workspace items with their Git repositories** (the docs say *synchronize*; the portal says *sync*)
- **Users can sync workspace items with GitHub repositories** (warning *Multi-geo restrictions are not enforced for items connected to GitHub* is harmless here: one region, and Git stores code, not data)

### 0.3 Workspace ✅

Workspace `nyc-analytics`, **Workspace settings** → **Workspace type** = Fabric Trial capacity.

### 0.4 Runtime 2.0 ✅

**Workspace settings** → **Data Engineering/Science** → **Spark settings** → **Environment** tab →
**Runtime version** → **2.0 (Spark 4.1, Delta 4.2)** → **Save**. Record it in README (Fabric runtime section).

### 0.5 Lakehouses and Warehouse ✅ (lh_bronze, lh_silver without schemas; wh_gold)

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

### 0.6 Connect the workspace to GitHub ✅ (Fabric commit `afc2dac`)

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

What Fabric wrote to `fabric/` on the first sync (real format, inspected after `git pull`):

| Item folder | Files | Meaning |
|---|---|---|
| `lh_bronze.Lakehouse/`, `lh_silver.Lakehouse/` | `.platform`, `lakehouse.metadata.json` (`{}`), `shortcuts.metadata.json` (`[]`), `alm.settings.json` | Only the definition: type, display name, a `logicalId`, shortcut settings. No data. |
| `wh_gold.Warehouse/` | `.platform`, `wh_gold.sqlproj`, `.gitignore`, `.gitattributes` | An SDK-style **SQL database project** (`Microsoft.Build.Sql`). Tables and procedures will appear as `.sql` files. |

`.platform` holds `metadata.type`, `metadata.displayName` and `config.logicalId`. Never edit the logicalId.
The Warehouse default collation is **`Latin1_General_100_BIN2_UTF8`**, so string comparisons are
**case-sensitive** (`'Outside NYC' <> 'outside nyc'`).

---

## Phase 1: ingestion

### 1.1 Secret: OpenAQ key in a Lakehouse file

Constraints:
- OpenAQ accepts the key only as the `X-API-Key` **header**. Fabric's "Web API" key credential sends the key
  as a URL query parameter, and OpenAQ rejects that with 401. So a stored connection credential cannot carry it.
- No Azure subscription, so Azure Key Vault is not available.

Chosen design: the key is a one-line text file in **`lh_bronze` → Files → `secrets/openaq_api_key.txt`**,
uploaded by hand once. `df_openaq` reads the file with the Lakehouse connector and puts it into the request header.

```
lh_bronze/Files/secrets/openaq_api_key.txt ──Lakehouse connector──▶ df_openaq ──X-API-Key header──▶ OpenAQ
```

Why it stays out of Git and logs:
- Fabric Git integration stores item **definitions** only; Lakehouse files and tables are never synced to Git.
- The key is not a pipeline or Dataflow parameter, so it does not appear in run inputs or outputs.

Trade-off compared with Key Vault: the file is plain text inside OneLake (encrypted at rest by the platform).
Anyone with read access to `lh_bronze` can open it, there is no audit log of who read the secret, and
rotation means uploading a new file. For a single-user course workspace this is acceptable. It is the
simplest option that works without Azure. Rule: Silver notebooks never read `Files/secrets/`.

Steps:
1. Create the file locally **outside the repo** (it must contain only the key):
   `! grep '^OPENAQ_API_KEY=' .env | cut -d= -f2- | tr -d '\n' > ~/openaq_api_key.txt`
2. `lh_bronze` → **Files** → **…** → **New subfolder** `secrets` → open it → **Upload** → **Upload files** →
   `~/openaq_api_key.txt`.
3. Delete the local copy: `! rm ~/openaq_api_key.txt`.

Fallback, if the Dataflow cannot combine the Lakehouse file with the web source (*Formula.Firewall* error)
even inside one query: a small notebook reads the file and returns it with `notebookutils.notebook.exit`
(activity **Secure output** ✓), and the pipeline passes it to a required Dataflow public parameter
(activity **Secure input** ✓).

### 1.2 Pipeline `pl_ingest` (rows 1–5 ✅ 2026-11-12)

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
| 6 | **Dataflow** `Run df_ecb`, `Run df_worldbank`, `Run df_openaq` | Workspace `nyc-analytics`, dataflow = the matching item. No parameters: each dataflow reads the config and (OpenAQ) the key from `lh_bronze` Files. |

Connect 1 → 2 → (3, 4, 5) and 1 → 6 with **On success** arrows (the dataflows only need the config file, not the Lookup output). **Save**, then **Run**.
Check the **Output** tab below the canvas.

Ingestion metadata for files: Bronze files stay byte-for-byte unchanged. The source and month are in
the folder and file name. The Silver notebook adds `source_file` and `load_ts` from Spark's file
metadata (`_metadata.file_path`, `_metadata.file_modification_time`).

### 1.3 Dataflows Gen2 ✅ (2026-11-12)

The M code lives in `drafts/dataflows/` (`df_ecb.pq`, `df_worldbank.pq`, `df_openaq.pq`). Each file was
syntax-checked locally with `@microsoft/powerquery-parser`. Copy the code from the GitHub raw URL in a
browser, not from a terminal: terminal line wrapping broke long lines twice ("Token ',' expected").

For each dataflow: workspace `nyc-analytics` → **+ New item** → **Dataflow Gen2** → name → **Create**.
**Get data** → **Blank query** → replace the template with the file's code → rename the query to the
Bronze table name from config (`ecb.bronze_table`, …).

**Config is read from `lh_bronze/Files/config/sources.json`**, the copy made by `Copy config` in
`pl_ingest`, not from GitHub. Reason: reading the GitHub raw URL from `df_openaq` returned an old
version of the file without `openaq.locations_path` (cached). Reading the Lakehouse copy also gives
one order: the pipeline refreshes the config first, then the dataflows read it.

The first steps of each query (`Lakehouse.Contents` → workspace → lakehouse → `Files`) were generated
by the Lakehouse connector (**Get data** → **Lakehouse** → `lh_bronze` → **Files**). The workspace and
lakehouse IDs are not secrets.

`df_openaq` reads the OpenAQ key from `Files/secrets/openaq_api_key.txt` in the **same** query and sends
it as the `X-API-Key` header. Never open the `ApiKey` step preview in a screenshot.

Connections and privacy levels:
- web sources (`api.worldbank.org`, `data-api.ecb.europa.eu`, `api.openaq.org`): Authentication **Anonymous**
  (the OpenAQ key goes in the header, not the connection);
- privacy level **Organizational** for the Lakehouse and every web source used with it in one query.
  Mixing Organizational (Lakehouse) and Public (web) triggers the *Formula.Firewall* error.

Destination: **Add data destination** → **Lakehouse** → `lh_bronze` → `dbo` → **Choose** →
**Bind selected queries**. Column mapping: accept the defaults. Update method **Replace**.
Notes from the first run:
- A dataflow run can say **Succeeded** without writing anything if the query has no destination. Always
  check the table itself.
- A new table can show up under **Tables → Unidentified** for a few minutes. **Refresh** the Tables folder.
- Lakehouse destinations do **not** support `DateTimeZone`, so `load_ts` is a UTC `datetime`.

Rate limits: `df_openaq` makes 1 + (number of sensors) requests, about 25, under the 60 requests/minute limit.
The paging stops when a page is shorter than `limit`, because `meta.found` can be the text `">1000"`.
`Num` formats numbers with `en-US`, so 40.7128 never becomes "40,7128".

After the items are committed from Fabric (**Source control** → **Commit**), I `git pull` and replace the
drafts with the real `fabric/<name>.Dataflow/` item files, so the M code has one home only.

### 1.4 First checks

- `lh_bronze` → **Files**: `config/sources.json`, `taxi/yellow_tripdata_2024-0[1-6].parquet`,
  `taxi_zones/taxi_zone_lookup.csv`, `reference/monitor_zones.csv`.
- `lh_bronze` → **Tables**: the three `bronze_*` tables, row counts close to `docs/sources.md`
  (OpenAQ ≈ 24 sensors × ~180 days; GDP 66 rows; ECB ~7,200 rows).
- `lh_bronze` → **Files** → `secrets/` contains only `openaq_api_key.txt`; nothing else reads this folder.

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
