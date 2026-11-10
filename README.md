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

PySpark needs Java 17 (`JAVA_HOME`).

## How to run

_TODO (Phase 5): orchestration pipeline and schedule._

## How to add a new source

_TODO: filled in when the framework is in place (add a block to `config/sources.json`,
one library notebook with a transform function, one Gold table)._
