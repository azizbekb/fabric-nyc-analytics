# NYC Unified Analytics on Microsoft Fabric

Course project (Itransition, Data Engineering). One analytics platform that combines
**mobility** (NYC Yellow Taxi), **environment** (OpenAQ air quality) and **economy**
(World Bank GDP, ECB USD/EUR) using the medallion architecture **Bronze → Silver → Gold**.

## Architecture

| Layer | Fabric item | Content |
|---|---|---|
| Bronze | Lakehouse `lh_bronze` | Raw data, unchanged, plus ingestion metadata |
| Silver | Lakehouse `lh_silver` | Cleaned, typed, deduplicated Delta tables + quarantine tables |
| Gold | Warehouse | Star schema (facts + dimensions) |
| Report | Power BI | Dashboards on the Warehouse semantic model |

Ingestion: Data Pipeline (taxi files) and Dataflow Gen2 (APIs). Transformation: PySpark notebooks.
See [docs/lineage.md](docs/lineage.md).

## Repository layout

```
config/sources.json   single source of truth: sources, months, table names
reference/            small committed reference data (monitor_zones.csv)
scripts/              local one-off scripts (profiling, monitor mapping)
fabric/               Fabric Git integration folder (*.Notebook, *.DataPipeline, ...)
tests/                pytest tests; they load library notebook source files directly
docs/                 data dictionary, lineage, governance, data profile, sources, setup_fabric
DEFENSE.md            defense notes (Uzbek)
```

## Setup from scratch

Step by step: [docs/setup_fabric.md](docs/setup_fabric.md) (Phase 0: capacity, workspace, Runtime 2.0, lakehouses, warehouse, Git; Phase 1: pipeline and dataflows; Phase 3: warehouse; Phase 5: orchestration and schedule).

### Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # put your OPENAQ_API_KEY here; .env is git-ignored
```

PySpark 4.1 needs Java 17 or newer. `JAVA_HOME` is exported in `.venv/bin/activate`.

### How to run tests

```bash
./scripts/run_tests.sh              # all tests; expected last line: "16 passed"
./scripts/run_tests.sh -k taxi      # only tests whose name contains "taxi"
```

The script activates `.venv` (Python + `JAVA_HOME`) and runs `pytest`. Running plain `pytest`
without the activated venv fails with errors at Spark start-up, because Java is not found.
Tests load the library notebooks exactly as Fabric runs them (see `tests/notebook_loader.py`).

### Local Gold check

```bash
source .venv/bin/activate
python scripts/check_gold.py 2024-01   # needs data/yellow_tripdata_2024-01.parquet and data/ecb_fx.csv
```

### Fabric runtime

The workspace uses **Fabric Runtime 2.0** (Spark 4.1, Python 3.13, Delta 4.2). Runtime 1.3 is in
end-of-support. Local tests use the same Spark version (`pyspark==4.1.1`).
Set in **Workspace settings** → **Data Engineering/Science** → **Spark settings** → **Environment** → **Runtime version** 2.0.

## How to run

Everything runs from one pipeline, **`pl_daily`** (scheduled daily at 06:00, Tashkent time):

```
Copy config → Lookup config → taxi months, zone files ┐
            └→ df_ecb, df_worldbank, df_openaq ────────┴→ nb_silver → refresh lh_silver endpoint
                                                          → Gold procedures (sequential) → refresh model
```

Manual run: open `pl_daily` → **Run**, then watch the **Output** tab (about 8 minutes).
To change months, sources or quality limits, edit `config/sources.json` and push: the pipeline copies
the config from GitHub at the start of each run. Details: [docs/setup_fabric.md](docs/setup_fabric.md#phase-5-orchestration-and-schedule).

## How to add a new source

Example: a new API source `<name>`. No existing code changes, only additions.

1. **Config.** Add a block to `config/sources.json`: `type`, `base_url`, `path`, `bronze_table`,
   `silver_table`, `quarantine_table`, `library` and any quality limits. Push.
2. **Bronze.** API: create Dataflow Gen2 `df_<name>` that reads `Files/config/sources.json` from
   `lh_bronze` (same first steps as `df_worldbank`), writes the `bronze_table` with **Replace**, and adds
   `source` and `load_ts`. File: add a **Copy data** activity in `pl_daily` with paths from config.
   Record the Bronze columns in [docs/sources.md](docs/sources.md#bronze-contract-for-api-tables).
3. **Silver rules.** Create notebook `nb_lib_<name>` with a pure function
   `transform_<name>(df) -> (silver, rejected)`, built from `split_by_rules` and `keep_first` in
   `nb_lib_common`, so every rejected row gets a `reject_reason`. Add `tests/test_<name>.py` and run `pytest`.
4. **Silver run.** In `nb_silver` add `%run nb_lib_<name>` and one cell like the World Bank one:
   ```python
   src = cfg["<name>"]
   raw = bronze_table(src)
   save_split(src, *transform_<name>(raw), raw.count())   # asserts silver + quarantine = Bronze rows
   ```
5. **Pipeline.** Add the dataflow activity to `pl_daily` and an **On success** arrow from it to `Run nb_silver`.
6. **Gold (if needed).** Create the table and a `load_<table>` procedure in `wh_gold`, then add the
   procedure name to `gold.load_procedures` in config. The pipeline itself does not change.
7. **Docs.** Add the tables to [docs/data_dictionary.md](docs/data_dictionary.md) and [docs/lineage.md](docs/lineage.md).
8. Commit from Fabric (Source control), then `git pull` locally.

A new taxi month needs only step 1: add it to `taxi.months`.

### When air quality monitors change

Monitor → taxi zone / borough mapping is a committed reference file, built locally with geopandas
(Fabric needs no geo libraries):

```bash
python scripts/map_monitors_to_zones.py   # uses openaq + taxi_zones settings from config
git add reference/monitor_zones.csv && git commit -m "Refresh monitor zones" && git push
```

Run it again after changing `openaq.parameters`, `radius_m` or `monitors_only`, or when OpenAQ adds a monitor.
Monitors outside NYC get `borough = "Outside NYC"` and an empty zone.
