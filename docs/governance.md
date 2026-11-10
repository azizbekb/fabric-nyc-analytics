# Governance

## Data quality rules

Principle: **no row is silently dropped.** An invalid row either goes to a quarantine
table with a `reject_reason` column, or stays in Silver with a flag column.
Concrete rules: _TODO (Step B, from `docs/data_profile.md`)._

## Quarantine

_TODO: quarantine tables, reasons, how to review them._

## Refresh schedule

_TODO (Phase 5): one daily orchestration pipeline: ingestion → silver notebooks → gold load._

## Access

_TODO: workspace roles; RLS optional._

## Secrets

- No secret is committed. `.env` is git-ignored; `.env.example` holds only key names.
- Locally the OpenAQ key is read from `OPENAQ_API_KEY`.
- In Fabric: _TODO (Phase 1): decide between connection credentials, a runtime parameter, or Key Vault._
