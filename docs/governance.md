# Governance

## Data quality rules

Principle: **no row is silently dropped.** An invalid row either goes to a quarantine
table with a `reject_reason` column, or stays in Silver with a flag column.
Concrete rules (proposed, from profiling): see [data_profile.md](data_profile.md#proposed-silver-rules).

## Quarantine

_TODO: quarantine tables, reasons, how to review them._

## Refresh schedule

_TODO (Phase 5): one daily orchestration pipeline: ingestion → silver notebooks → gold load._

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
