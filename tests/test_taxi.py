from notebook_loader import load_libs

lib = load_libs("nb_lib_common", "nb_lib_taxi")

RAW_SCHEMA = (
    "VendorID int, tpep_pickup_datetime string, tpep_dropoff_datetime string, passenger_count bigint, "
    "trip_distance double, RatecodeID bigint, PULocationID int, DOLocationID int, payment_type bigint, "
    "fare_amount double, total_amount double, Airport_fee double"
)

# (name, pickup, dropoff, passengers, distance, fare, total, pu_zone)
TRIPS = [
    ("normal",        "2024-01-10 08:00:00", "2024-01-10 08:20:00", 1,    3.0,   15.0,  20.0, 100),
    ("zero_distance", "2024-01-10 09:00:00", "2024-01-10 09:05:00", 1,    0.0,    5.0,   8.0, 101),
    ("no_passengers", "2024-01-10 10:00:00", "2024-01-10 10:10:00", None, 2.0,   10.0,  12.0, 102),
    ("outlier",       "2024-01-10 11:00:00", "2024-01-10 11:30:00", 1,  500.0,   40.0,  45.0, 103),
    ("void_charge",   "2024-01-11 12:00:00", "2024-01-11 12:05:00", 1,    1.0,    6.5,  10.5, 104),
    ("void_cancel",   "2024-01-11 12:00:00", "2024-01-11 12:05:00", 1,    1.0,   -6.5, -10.5, 104),
    ("negative",      "2024-01-12 13:00:00", "2024-01-12 13:10:00", 1,    2.0,   -9.0,  -9.0, 105),
    ("year_2002",     "2002-12-31 22:59:00", "2002-12-31 23:05:00", 1,    1.0,    6.5,  10.5, 106),
    ("dropoff_first", "2024-01-13 14:00:00", "2024-01-13 13:50:00", 1,    1.0,    6.5,  10.5, 107),
    ("too_long",      "2024-01-14 00:00:00", "2024-01-15 02:00:00", 1,    1.0,    6.5,  10.5, 108),
    ("dup_a",         "2024-01-16 15:00:00", "2024-01-16 15:10:00", 1,    2.0,   12.0,  15.0, 109),
    ("dup_b",         "2024-01-16 15:00:00", "2024-01-16 15:10:00", 1,    2.0,   12.0,  15.0, 109),
]


def raw_trips(spark):
    rows = [(2, pu, do, pax, dist, 1, zone, 200, 1, fare, total, 0.0) for _, pu, do, pax, dist, fare, total, zone in TRIPS]
    return spark.createDataFrame(rows, RAW_SCHEMA).withColumns({
        "tpep_pickup_datetime": lib.F.col("tpep_pickup_datetime").cast("timestamp_ntz"),
        "tpep_dropoff_datetime": lib.F.col("tpep_dropoff_datetime").cast("timestamp_ntz"),
    })


def run(spark, config):
    return lib.transform_trips(raw_trips(spark), "2024-01", config["taxi"]["quality"])


def test_no_row_is_lost(spark, config):
    silver, quarantine = run(spark, config)
    assert silver.count() + quarantine.count() == len(TRIPS)


def test_quarantine_reasons(spark, config):
    _, quarantine = run(spark, config)
    reasons = {r.pu_location_id: r.reject_reason for r in quarantine.collect()}
    assert reasons == {
        105: "negative_amount",
        106: "pickup_outside_file_month",
        107: "dropoff_before_pickup",
        108: "duration_over_limit",
        109: "duplicate",
    }


def test_flags_and_attributes(spark, config):
    silver, _ = run(spark, config)
    rows = {r.pu_location_id: r for r in silver.collect()}
    assert rows[101].trip_distance == 0.0 and not rows[101].is_outlier
    assert rows[102].is_passenger_count_missing and rows[102].passenger_count is None
    assert rows[103].is_outlier
    assert sum(r.is_void for r in silver.collect()) == 2
    assert (rows[100].pickup_date.isoformat(), rows[100].pickup_hour, rows[100].trip_duration_min) == ("2024-01-10", 8, 20.0)
    assert "airport_fee" in silver.columns


def test_zones_cast_location_id(spark):
    df = spark.createDataFrame([("264", "Unknown", "N/A", "N/A")], "LocationID string, Borough string, Zone string, service_zone string")
    row = lib.transform_zones(df).first()
    assert (row.location_id, row.borough) == (264, "Unknown")
