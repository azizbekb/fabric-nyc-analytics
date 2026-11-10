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
drafts/               library code before the Fabric notebook items exist (temporary)
reference/            small committed reference data (monitor_zones.csv)
scripts/              local one-off scripts (profiling, monitor mapping)
fabric/               Fabric Git integration folder (*.Notebook, *.DataPipeline, ...)
tests/                pytest tests; they load library notebook source files directly
docs/                 data dictionary, lineage, governance, data profile, sources
DEFENSE.md            defense notes (Uzbek)
```

## Setup from scratch

_TODO (Phase 0): Fabric workspace, lakehouses, warehouse, Git connection._

### Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # put your OPENAQ_API_KEY here; .env is git-ignored
pytest
```

PySpark 4.1 needs Java 17 or newer (`JAVA_HOME`).

Tests load the library notebooks exactly as Fabric runs them (see `tests/notebook_loader.py`):

```bash
pytest -q
```

### Fabric runtime

The workspace uses **Fabric Runtime 2.0** (Spark 4.1, Python 3.13, Delta 4.2). Runtime 1.3 is in
end-of-support. Local tests use the same Spark version (`pyspark==4.1.1`).
_TODO (Phase 0): record where it is set (Workspace settings → Data Engineering/Science → Spark settings → Environment)._

## How to run

_TODO (Phase 5): orchestration pipeline and schedule._

## How to add a new source

_TODO: full steps when the pipelines exist. Shape: add a block to `config/sources.json`,
one library notebook `nb_lib_<name>` with a pure transform function plus a test, one Gold table._

### When air quality monitors change

Monitor → taxi zone / borough mapping is a committed reference file, built locally with geopandas
(Fabric needs no geo libraries):

```bash
python scripts/map_monitors_to_zones.py   # uses openaq + taxi_zones settings from config
git add reference/monitor_zones.csv && git commit -m "Refresh monitor zones" && git push
```

Run it again after changing `openaq.parameters`, `radius_m` or `monitors_only`, or when OpenAQ adds a monitor.
Monitors outside NYC get `borough = "Outside NYC"` and an empty zone.
