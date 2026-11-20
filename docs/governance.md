# Governance

## Data quality rules

Principle: **no row is silently dropped.** An invalid row either goes to a quarantine
table with a `reject_reason` column, or stays in Silver with a flag column.
Concrete rules (proposed, from profiling): see [data_profile.md](data_profile.md#proposed-silver-rules).

## Quarantine

Each Silver table with rules has a quarantine table in `lh_silver` with the same columns plus
`reject_reason`. `nb_silver` asserts that silver rows + quarantine rows = Bronze rows. Rows that are
usable but doubtful stay in Silver with a flag, so the report can include or exclude them.

Counts after the run of 2026-11-20 (months 2024-01 … 2024-06):

| Table | `reject_reason` | Rows | Rule |
|---|---|---:|---|
| `quarantine_taxi_trips` | `negative_amount` | 93,703 | fare or total < 0, and not part of a void pair |
| | `dropoff_before_pickup` | 300 | dropoff time earlier than pickup |
| | `pickup_outside_file_month` | 149 | pickup date not in the month of the file |
| | `duration_over_limit` | 109 | trip longer than `taxi.quality.max_duration_h` (24 h) |
| | `duplicate` | 36 | same trip key twice; the row with the highest total is kept |
| `quarantine_air_quality` | `value_null` | 3 | daily value missing |
| `quarantine_fx` | `value_null` | 62 | ECB row without a rate (holiday) |
| `quarantine_gdp` | — | 0 | rules `value_null`, `duplicate`; nothing rejected |

Flags in Silver (rows kept):

| Table | Flag | Rows | Meaning, effect in Gold |
|---|---|---:|---|
| `silver_taxi_trips` | `is_void` | 445,972 | charge + cancellation pair; excluded from `trips` and revenue |
| | `is_outlier` | 713 | distance > 100 mi or fare > $1,000; counted in `trips`, excluded from `clean_trips` and averages |
| | `is_passenger_count_missing` | 2,137,319 | passenger count NULL or 0; value kept, not used in any measure |
| `silver_air_quality` | `is_low_coverage` | 121 | under 75 % of hours measured; excluded from the PM2.5 / NO2 / O3 measures |

How to review: run [scripts/quarantine_summary.sql](../scripts/quarantine_summary.sql) on the `lh_silver`
SQL analytics endpoint after a run. A sudden jump in one reason means a source changed. To look at the
rows, query the quarantine table filtered by `reject_reason` (taxi rows keep `source_file`). Limits live
in `config/sources.json` (`taxi.quality`, `openaq.min_coverage_pct`), so a rule changes without code changes.

## Refresh schedule

One pipeline, `pl_daily`, runs the whole flow **every day at 06:00 Tashkent time** (Fabric schedule,
committed as `fabric/pl_daily.DataPipeline/.schedules`):

1. Bronze: config copy, taxi months, zone files, three dataflows;
2. `nb_silver` (starts only after **all** Bronze activities succeed);
3. refresh of the `lh_silver` SQL analytics endpoint;
4. Gold stored procedures, one by one, in the order of `gold.load_procedures` in config;
5. refresh of the semantic model `sm_nyc_analytics`.

Every step depends on the previous one **On success**, so a failure stops all later steps: Gold is never
loaded from a half-finished Silver run. Every step overwrites or replaces its output, so a rerun
is safe. Failures are visible in **Monitor** (e-mail alerts work only for addresses inside the tenant).

## Access

Today the workspace `nyc-analytics` has one member, the project owner, with the **Admin** role
(single-person course project). The pipeline connections (SQL endpoint refresh, semantic model refresh)
use the owner's organizational account, so the schedule runs with the owner's rights.

Role model for a team (workspace → **Manage access**):

| Who | Role | Can |
|---|---|---|
| Platform owner | Admin | everything, including access and Git settings |
| Data engineers | Contributor | edit pipelines, notebooks, warehouse; commit to Git |
| Analysts / report readers | the report shared alone (or Viewer) | read the report; Viewer also reads tables through the SQL endpoints |

Note: Admin, Member and Contributor can read Lakehouse files through OneLake, so the OpenAQ key file is
visible to them (see [Secrets](#secrets)). Keep those roles for people who build the platform; report
readers get the report, not an editing role. Row-level security is optional in the brief and not used: all data is public and every
reader may see every borough.

## Secrets

- No secret is committed. `.env` is git-ignored; `.env.example` holds only key names.
- Locally the OpenAQ key is read from `OPENAQ_API_KEY`.
- OpenAQ accepts the key **only as the `X-API-Key` header** (a query parameter returns 401), so a Dataflow must send it in `Web.Contents(..., [Headers = ...])`.
- In Fabric (no Azure subscription, so no Key Vault): the key is a one-line file
  `lh_bronze/Files/secrets/openaq_api_key.txt`, uploaded by hand. `df_openaq` reads it with the Lakehouse
  connector. Lakehouse data is never synced to Git, and the key is not a pipeline parameter, so it does not
  appear in run logs. Trade-off: plain text in OneLake, readable by anyone with read access to `lh_bronze`,
  no audit log, manual rotation (upload a new file). Silver notebooks never read `Files/secrets/`.
  Details: [setup_fabric.md §1.1](setup_fabric.md#11-secret-openaq-key-in-a-lakehouse-file).
