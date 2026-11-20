# Governance

## Data quality rules

Principle: **no row is silently dropped.** An invalid row either goes to a quarantine
table with a `reject_reason` column, or stays in Silver with a flag column.
Concrete rules (proposed, from profiling): see [data_profile.md](data_profile.md#proposed-silver-rules).

## Quarantine

_TODO: quarantine tables, reasons, how to review them._

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

_TODO: workspace roles; RLS optional._

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
