# Data Dictionary

Every table and column per layer: type, meaning, source. Filled in as tables are built.

## Bronze

_TODO (Phase 1)._ API table columns are fixed in [sources.md](sources.md#bronze-contract-for-api-tables).

## Silver

All Silver tables keep the Bronze columns (snake_case) plus the columns below.
Each quarantine table has the same columns as its input plus `reject_reason` (string).

### silver_taxi_trips / quarantine_taxi_trips

Source: TLC Yellow Taxi Parquet. One row per trip record. Library: `nb_lib_taxi.transform_trips`.

| Column | Type | Meaning |
|---|---|---|
| vendor_id … airport_fee | as source | TLC columns renamed to snake_case; `passenger_count`, `ratecode_id`, `payment_type` cast to int |
| pickup_date | date | local NYC date of pickup |
| pickup_hour | int | 0–23 |
| trip_duration_min | double | dropoff − pickup in minutes |
| is_void | boolean | row is half of a charge + cancellation pair (sum of total_amount = 0) |
| is_outlier | boolean | trip_distance > `max_distance_mi` or fare_amount > `max_fare_usd` |
| is_passenger_count_missing | boolean | passenger_count NULL or 0 (value kept as is) |

Quarantine reasons: `pickup_outside_file_month`, `dropoff_before_pickup`, `duration_over_limit`,
`negative_amount`, `duplicate`.

### silver_taxi_zones

Source: `taxi_zone_lookup.csv`. `location_id` int, `borough`, `zone`, `service_zone` (string).

### silver_air_quality / quarantine_air_quality

Source: OpenAQ `/sensors/{id}/days`. One row per sensor and day. Library: `nb_lib_openaq.transform_air_quality`.

| Column | Type | Meaning |
|---|---|---|
| date | date | local NYC day (from `period_start_local`) |
| value | double | daily mean, in `units` |
| is_low_coverage | boolean | percent_complete < `min_coverage_pct` |
| has_source_flags | boolean | OpenAQ flagged at least one hour of the day |

Quarantine reasons: `value_null`, `value_negative`, `duplicate`.

### silver_monitor_zones

Source: `reference/monitor_zones.csv`. `location_id` int, `location_name`, `latitude`/`longitude` double,
`zone_id` int (NULL outside NYC), `zone`, `borough` (`Outside NYC` for New Jersey).

### silver_gdp

Source: World Bank. `country_code`, `indicator_id`, `year` int, `gdp_usd` double (current USD).
Quarantine reasons: `value_null`, `duplicate`.

### silver_fx_daily

Source: ECB. One row per calendar day.

| Column | Type | Meaning |
|---|---|---|
| date | date | calendar day |
| usd_per_eur | double | USD for 1 EUR; on days without a rate, the last earlier rate |
| is_filled | boolean | true when the rate was carried forward (weekend / holiday) |

## Gold

_TODO (Phase 3)_
