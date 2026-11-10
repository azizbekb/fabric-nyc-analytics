# Sources

Results of test requests made on 2026-11-10. All values that code needs are in `config/sources.json`.

## OpenAQ API v3

- Base URL `https://api.openaq.org/v3`. Auth: header **`X-API-Key`** only. A query parameter
  (`api_key`, `apikey`) returns 401, so the key must travel in a header.
- Rate limit (free key): **60 requests/min, 2,000/hour**. Response headers `x-ratelimit-remaining`
  and `x-ratelimit-reset` (seconds); HTTP 429 when exceeded.
- Pagination: `page` + `limit` (we use 1000). `meta.found` is sometimes a **string** like `">1000"`,
  so paging stops when a page returns fewer than `limit` rows, not by comparing with `found`.

### Endpoints we use

| Step | Endpoint | Parameters |
|---|---|---|
| 1. Locations near NYC | `GET /locations` | `coordinates=lat,lon` (latitude first!), `radius` in metres, **max 25,000**, `limit` |
| 2. Daily values per sensor | `GET /sensors/{sensor_id}/days` | `date_from`, `date_to` (both **inclusive**), `limit`, `page` |

The `/locations` response already contains each location's `sensors` (id + parameter + units), so a
separate `/locations/{id}/sensors` call is not needed.

**Trap:** parameter names differ per endpoint, and a wrong name is **silently ignored** (the API then
returns the full history since 2016):

| Endpoint | Date params | `to` bound |
|---|---|---|
| `/sensors/{id}/days` (precomputed) | `date_from`, `date_to` | inclusive |
| `/sensors/{id}/measurements/daily` (computed on request) | `datetime_from`, `datetime_to` | exclusive |

We use `/days` (precomputed, so faster). The date range is derived from `taxi.months`: from the first
day of the first month to the last day of the last month. That way, adding a month is still one config change.

### Daily result fields

| Field | Meaning |
|---|---|
| `value` | daily mean |
| `parameter.name`, `parameter.units` | `pm25` µg/m³, `no2` ppm, `o3` ppm |
| `period.datetimeFrom.local` | start of the local NYC day (offset −05:00 / −04:00 with DST); its date part is our `date` |
| `summary.min`, `summary.max`, `summary.avg`, … | stats of the hourly values in that day |
| `coverage.percentComplete` | share of expected hourly values present (24 = 100%) |
| `flagInfo.hasFlags` | true if some hour of the day was flagged (all flags seen: "Limits exceeded", e.g. a negative hourly reading) |

### Location and sensor choice

Within 25 km of (40.7128, −74.0060) there are 76 locations: 26 AirNow government monitors
(`isMonitor = true`) and 50 low-cost sensors (AirGradient, Clarity). We use **monitors only**
(`monitors_only: true`), because they are reference-grade instruments and the low-cost sensors mostly
do not cover 2024.

Monitor sensors for our parameters with data in 2024-01-01 … 2024-06-30:

| Parameter | Sensors with data | Days (of 182) | Notes |
|---|---|---|---|
| pm25 | 14 | 165–182 | some days have `hasFlags` (up to 111 per sensor); 3 days with `value = null` |
| o3 | 6 | 136–182 | |
| no2 | 4 | 178–182 | **all 4 are in New Jersey** (Fort Lee, Bayonne, Elizabeth, Jersey City); no NYC NO2 monitor in range |

10 monitor sensors return no data for this period. Selection is not hard-coded: the Dataflow takes
every monitor sensor of a configured parameter, and sensors without data simply return no rows.

Daily coverage is high (average 86–99%). Days below 75% exist on most sensors (2–14 days).

### Proposed Silver rules (air quality)

| Case | Action |
|---|---|
| `value` is null | quarantine, `reject_reason = value_null` |
| `value` < 0 | quarantine, `reject_reason = value_negative` (none seen at daily level) |
| `coverage.percentComplete` < `min_coverage_pct` (75) | keep, flag `is_low_coverage` |
| `flagInfo.hasFlags` = true | keep, flag `has_source_flags` |
| Duplicate (sensor, date) | keep one, extra row to quarantine `duplicate` |

### Limitations

- **NO2 comes only from New Jersey monitors** (Fort Lee, Bayonne, Elizabeth, Jersey City). Within
  25 km there is no NO2 monitor inside NYC, so NO2 trends describe the regional air, not a borough.
- **Daily granularity only.** We load `/days`, so air quality has no time of day. Hour-of-day analysis
  (rush hours, night) is possible only for taxi data, unless `/sensors/{id}/hours` is loaded later
  (about 24× more rows, same paging).
- Monitors are points. Fact rows are at monitor level, and the taxi correlation uses the **city-wide
  daily average** of all monitors per pollutant, not a per-zone value.

## World Bank GDP

- `GET https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=100`
- No key. The response is a JSON **array of two elements**: `[meta, data]`.
  `meta` = `{page, pages, per_page, total, lastupdated}`.
- 66 yearly rows (1960–2025), so `per_page=100` gives one page. Paging is still implemented
  (`page` from 1 to `meta.pages`) in case the series grows. With `per_page=10` we saw `pages = 7`.
- Fields: `date` (year, **string**), `value` (current USD, number, may be null), `countryiso3code`,
  `indicator.id`, `obs_status`. No null values today.
- Rows come newest first. `lastupdated` = 2026-10-08.

## ECB USD/EUR

- `GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata`, no key,
  `text/csv`. The full series (1999 → today) is ~7,200 rows / 1.4 MB, so we load it fully; `startPeriod` /
  `endPeriod` work but are not needed.
- Columns used: `TIME_PERIOD` (date), `OBS_VALUE` (**USD per 1 EUR**, e.g. 1.1065), `OBS_STATUS`.
  The other 29 columns are metadata and stay in Bronze unchanged.
- **No rates on weekends and TARGET holidays.** Example: 2023-12-29 → next rate 2024-01-02
  (missing 12-30, 12-31, 01-01). 12-25 and 12-26 are also missing.
- Mapping rule (`missing_day_rule: last_available`): Silver builds one row per calendar day, and a
  day without a rate takes the last earlier published rate (forward fill), with flag `is_filled = true`.
  Because we load the full history, the first days of any taxi month always have an earlier rate.
- **Old holiday rows:** 62 rows (1999–2012) have an empty `OBS_VALUE` with `OBS_STATUS = 'H'`, i.e. the ECB
  published the holiday as a row without a rate. Silver sends them to quarantine (`value_null`) and the calendar
  fill gives those days the last earlier rate, exactly like a weekend.
- Conversion: `amount_eur = amount_usd / usd_per_eur`.

## Bronze contract for API tables

Dataflows Gen2 (Phase 1) flatten the JSON/CSV into these columns. The Silver library functions
expect exactly these names, and the Dataflow M code must produce them.
Every table also gets the ingestion metadata columns `source` and `load_ts`.

| Table | Columns |
|---|---|
| `bronze_openaq_measurements` | `location_id`, `location_name`, `sensor_id`, `parameter`, `units`, `period_start_local` (text, ISO with offset), `value`, `value_min`, `value_max`, `percent_complete`, `has_source_flags` |
| `bronze_worldbank_gdp` | `country_code`, `indicator_id`, `year` (text), `value` |
| `bronze_ecb_fx` | all CSV columns unchanged (`KEY`, `TIME_PERIOD`, `OBS_VALUE`, `OBS_STATUS`, …) |

## Monitor → taxi zone reference

`reference/monitor_zones.csv` maps each selected monitor to its TLC taxi zone / borough
(point-in-polygon with geopandas on the official TLC shapefile `taxi_zones.zip`, EPSG:2263).
It is built locally by `scripts/map_monitors_to_zones.py` and committed. Fabric only reads the CSV.
Result today: 25 monitors, 14 inside NYC (all 5 boroughs), 11 `Outside NYC` (New Jersey).

## NYC TLC

See [data_profile.md](data_profile.md). Monthly Parquet, ~50 MB per month, no key.
