# Data Dictionary

Every table and column per layer: type, meaning, source.

## Bronze

Lakehouse `lh_bronze`. Raw data, unchanged. Files are byte-for-byte copies; API tables are flattened
by the dataflows and get `source` and `load_ts`. API table columns: [sources.md](sources.md#bronze-contract-for-api-tables).

| Object | Kind | Content | Written by |
|---|---|---|---|
| `Files/taxi/yellow_tripdata_<month>.parquet` | file | TLC trip records, one file per month in `taxi.months` | `pl_daily` → `Copy taxi month` |
| `Files/taxi_zones/taxi_zone_lookup.csv` | file | 265 TLC zones | `pl_daily` → `Copy taxi zones` |
| `Files/reference/monitor_zones.csv` | file | monitor → zone mapping (copy of `reference/monitor_zones.csv`) | `pl_daily` → `Copy monitor zones` |
| `Files/config/sources.json` | file | copy of the repo config, read by the pipeline, dataflows and notebooks | `pl_daily` → `Copy config` |
| `Files/secrets/openaq_api_key.txt` | file | OpenAQ key, uploaded by hand, never in Git | manual |
| `bronze_openaq_measurements` | table | one row per sensor and day | `df_openaq` |
| `bronze_worldbank_gdp` | table | one row per year | `df_worldbank` |
| `bronze_ecb_fx` | table | one row per ECB working day | `df_ecb` |

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
Quarantine table `quarantine_gdp`, reasons: `value_null`, `duplicate`.

### silver_fx_daily

Source: ECB. One row per calendar day.

| Column | Type | Meaning |
|---|---|---|
| date | date | calendar day |
| usd_per_eur | double | USD for 1 EUR; on days without a rate, the last earlier rate |
| is_filled | boolean | true when the rate was carried forward (weekend / holiday) |

Quarantine table `quarantine_fx` (Bronze columns + `reject_reason`), reasons: `value_null` (ECB rows
without a rate), `duplicate`. Silver has one row per calendar day, so its count differs from Bronze.

## Gold

Warehouse `wh_gold`. DDL: `fabric/wh_gold.Warehouse/dbo/Tables/`; load procedures: `fabric/wh_gold.Warehouse/dbo/StoredProcedures/`
(full reload). Keys are `NOT ENFORCED` (Fabric). All money is in USD unless the name says `eur`.

| Table | Grain | Columns | Source |
|---|---|---|---|
| DimDate | 1 row per day from the first to the last fact day | date_key (yyyymmdd), date, year, quarter, month, month_name, day, day_of_week (1 = Mon), day_name, is_weekend | generated |
| DimZone | TLC zone | zone_id, borough, zone, service_zone | silver_taxi_zones |
| DimLocation | OpenAQ monitor | location_id, location_name, latitude, longitude, zone_id (NULL outside NYC), zone, borough | silver_monitor_zones |
| DimFX | day | date_key, date, usd_per_eur, is_filled | silver_fx_daily |
| DimGDP | year | year, country_code, gdp_usd | silver_gdp |
| FactTaxiDaily | day × pickup zone | trips (void pairs excluded), clean_trips (no outliers), total_fare_usd, total_amount_usd, total_amount_eur, avg_fare_usd, avg_distance_mi, avg_duration_min (averages over clean trips) | silver_taxi_trips + silver_fx_daily |
| FactAirQualityDaily | day × monitor × pollutant | parameter, units, avg_value, min_value, max_value, is_low_coverage | silver_air_quality |

`total_amount_eur = total_amount_usd / usd_per_eur` of the same day (weekends use the last available rate).

## Semantic model

`sm_nyc_analytics`, Direct Lake on `wh_gold`. Definition: `fabric/sm_nyc_analytics.SemanticModel/definition/`
(TMDL). `DimDate` is marked as the date table.

Relationships (all many-to-one, single direction): `FactTaxiDaily[date_key]` → `DimDate`,
`FactTaxiDaily[zone_id]` → `DimZone`, `FactAirQualityDaily[date_key]` → `DimDate`,
`FactAirQualityDaily[location_id]` → `DimLocation`, `DimFX[date_key]` → `DimDate`, `DimDate[year]` → `DimGDP`.

| Measure | Table | Meaning |
|---|---|---|
| Total Trips | FactTaxiDaily | sum of `trips` (void pairs excluded) |
| Clean Trips | FactTaxiDaily | sum of `clean_trips` (no outliers) |
| Revenue USD / Revenue EUR | FactTaxiDaily | sum of `total_amount_usd` / `total_amount_eur` |
| Avg Fare USD, Avg Distance mi, Avg Duration min | FactTaxiDaily | daily averages weighted by `clean_trips` |
| Trips per Day | FactTaxiDaily | Total Trips / number of days |
| Trips 7d Avg | FactTaxiDaily | average of daily trips over the last 7 days |
| Trips MoM % | FactTaxiDaily | change versus the previous month |
| Trips vs PM2.5 Correlation | FactTaxiDaily | Pearson correlation of daily trips and daily PM2.5 |
| PM2.5 Avg, NO2 Avg, O3 Avg | FactAirQualityDaily | average daily value, low-coverage days excluded |
| USD per EUR | DimFX | average rate |
| GDP USD bn | DimGDP | GDP of the selected years, in billions (`TREATAS` from `DimDate[year]`) |
