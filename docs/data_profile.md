# Data Profile: NYC Yellow Taxi 2024-01

Source: `yellow_tripdata_2024-01.parquet` (2,964,624 rows) and `taxi_zone_lookup.csv` (265 rows).
Reproduce: `python scripts/profile_taxi.py 2024-01` (local PySpark).

## Schema

| Column | Type | Nulls | Notes |
|---|---|---|---|
| VendorID | int | 0 | values 1, 2, 6 (6 = 260 rows; valid code in the TLC dictionary) |
| tpep_pickup_datetime | timestamp_ntz | 0 | local NYC time, no time zone |
| tpep_dropoff_datetime | timestamp_ntz | 0 | |
| passenger_count | bigint | 140,162 | |
| trip_distance | double | 0 | miles |
| RatecodeID | bigint | 140,162 | 99 = unknown (28,663 rows) |
| store_and_fwd_flag | string | 140,162 | Y / N |
| PULocationID, DOLocationID | int | 0 | all IDs exist in the zone lookup |
| payment_type | bigint | 0 | 0 = unknown (140,162 rows) |
| fare_amount … total_amount | double | 0 | 8 money columns |
| congestion_surcharge | double | 140,162 | |
| Airport_fee | double | 140,162 | capital `A` in this file; must be normalised to snake_case |

The **140,162 NULL rows** are the same rows: `passenger_count`, `RatecodeID`, `store_and_fwd_flag`,
`congestion_surcharge` and `Airport_fee` are NULL, and `payment_type = 0`, all at once (4.7%).
These rows have valid times, zones and amounts, so they are real trips with incomplete metadata.

Zone lookup: `LocationID` is read as string and must be cast to int. Two special zones:
264 = `Unknown / N/A`, 265 = `N/A / Outside of NYC`.

## Anomalies

| Check | Rows | % |
|---|---|---|
| Pickup before file month (2002-12-31: 2, 2009-01-01: 3, 2023-12-31: 10) | 15 | 0.0005 |
| Pickup after file month (2024-02-01) | 3 | 0.0001 |
| Dropoff before pickup | 56 | 0.002 |
| Duration > 24 h | 16 | 0.0005 |
| Duration = 0 | 814 | 0.03 |
| passenger_count NULL | 140,162 | 4.7 |
| passenger_count = 0 | 31,465 | 1.1 |
| trip_distance = 0 | 60,371 | 2.0 |
| trip_distance > 100 miles (max 312,722) | 59 | 0.002 |
| fare_amount < 0 | 37,448 | 1.3 |
| total_amount < 0 | 35,504 | 1.2 |
| fare_amount > 1000 (max 5000) | 7 | 0.0002 |
| Pickup in zone 264/265 | 12,018 | 0.4 |
| Exact duplicate rows | 0 | |

### Duplicates and void pairs

The natural key (`VendorID`, pickup time, dropoff time, `PULocationID`, `DOLocationID`) repeats in
31,109 groups, each with exactly 2 rows:

- **30,672 void pairs (61,344 rows):** one row has +X and the other −X, and `total_amount` sums to 0.
  This is a charge followed by its cancellation.
- **429 pairs (858 rows)** contain a negative row, but the two amounts do not sum to 0.
- **8 pairs** have no negative row. These are real duplicates.

Negative rows that are **not** part of a void pair: **6,896**.

Consequence: if we only removed negative rows, the matching positive rows would stay, and both
trips and revenue would be overstated by about 30k trips.

### Edge days

Inside the month, daily volume is normal from day 1 to day 31 (81k on 01-01, 102k on 01-31).
The out-of-month rows create tiny fake days: 2023-12-31 has 10 trips, 2024-02-01 has 3 trips.
These would show as a dip in a daily chart.

## Proposed Silver rules

Principle (rule 6): no row is silently dropped. Every row ends up in exactly one of
`silver_taxi_trips` (with flags) or `quarantine_taxi_trips` (with `reject_reason`).

**Quarantine.** The row cannot be trusted for analysis. Checks run in this order, and the first match is the reason:

| reject_reason | Rule | Rows in 2024-01 |
|---|---|---|
| `pickup_outside_file_month` | pickup date not in the month of the source file | 18 |
| `dropoff_before_pickup` | dropoff < pickup | 56 |
| `duration_over_limit` | dropoff − pickup > `max_duration_h` (24 h) | 16 |
| `negative_amount` | fare or total < 0 and the row is not part of a void pair | ≈ 6,896 |
| `duplicate` | second row of a natural-key group with no negative row | 8 |

**Keep in Silver, with a flag:**

| Flag column | Rule | Gold usage |
|---|---|---|
| `is_void` | row belongs to a zero-sum void pair (both rows) | excluded from trip counts and revenue |
| `is_outlier` | trip_distance > 100 miles or fare_amount > 1000 | counted as a trip, excluded from averages |
| `is_passenger_count_missing` | passenger_count NULL or 0 | value kept as is (no imputation), excluded from passenger averages |

**Keep without a flag (valid real trips):** `trip_distance = 0` (lecturer's rule), duration 0,
zones 264/265 (DimZone holds them as Unknown / Outside of NYC), RatecodeID 99, VendorID 6.

**Normalisation:** snake_case column names (e.g. `Airport_fee` → `airport_fee`), so that months
with different column spelling union cleanly. Code columns stay as numbers and are decoded later in
Gold or the report.

The thresholds (100 miles, 1000 USD, 24 h) live in `config/sources.json` → `taxi.quality`, not in code.

**Check on the real file** (`transform_trips` on 2024-01): silver 2,957,630 + quarantine 6,994 = 2,964,624 raw rows.
Quarantine: 18 / 56 / 16 / 6,896 / 8 (same as the profile). `is_void` = 61,340, not 61,344, because 2 void pairs
(e.g. the 2002 pair) are rejected earlier as `pickup_outside_file_month`.

## Open points

- Only one month was profiled. Column names and types must be checked for every configured month
  when the Silver notebook unions them.
- The 429 non-zero-sum negative pairs are counted under `negative_amount` (only their negative row).

## Gold check (local prototype)

`python scripts/check_gold.py 2024-01` rebuilds Silver from the raw file, aggregates it the same way as
`dbo.load_fact_taxi_daily` (PySpark copy of the SQL, used only for this check) and joins the ECB rates.

| Check | Result (2024-01) |
|---|---|
| Fact trips = Silver non-void trips | 2,896,290 = 2,896,290 |
| Fact total_amount_usd = Silver | 79,563,881.08 = 79,563,881.08 |
| Grain (date, zone) unique | 6,931 rows, no duplicates |
| All fact days inside the file month | yes, 31 days |
| Edge days within 0.5–2× of the median day (94,775) | 01-01: 0.83, 01-02: 0.78, 01-03: 0.85, 01-29: 0.87, 01-30: 1.05, 01-31: 1.05 |
| Every fact day has a USD/EUR rate | yes (01-01 holiday uses the 2023-12-29 rate 1.105, `is_filled`) |

Without the Silver rules, the raw file would add fake days to a daily chart: 2023-12-31 (10 trips),
2024-02-01 (3), plus 2002-12-31 and 2009-01-01. The lower 01-01 and 01-02 values are real (holiday period),
not partial data: each day has all its hours, because only out-of-month rows are removed.
