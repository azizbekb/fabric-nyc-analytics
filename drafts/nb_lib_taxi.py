# Silver transforms for NYC taxi trips and the zone lookup. Needs nb_lib_common (%run it first).
from pyspark.sql import Window, functions as F

TRIP_KEY = ["vendor_id", "tpep_pickup_datetime", "tpep_dropoff_datetime", "pu_location_id", "do_location_id"]


def normalize_trips(df):
    return snake_case_columns(df).withColumns({
        "passenger_count": F.col("passenger_count").cast("int"),
        "ratecode_id": F.col("ratecode_id").cast("int"),
        "payment_type": F.col("payment_type").cast("int"),
    })


def add_trip_attributes(df):
    pickup, dropoff = F.col("tpep_pickup_datetime"), F.col("tpep_dropoff_datetime")
    return df.withColumns({
        "pickup_date": F.to_date(pickup),
        "pickup_hour": F.hour(pickup),
        "trip_duration_min": (F.unix_timestamp(dropoff) - F.unix_timestamp(pickup)) / 60,
    })


def flag_void_pairs(df, tolerance):
    """A charge and its cancellation: two rows with the same trip key whose total_amount sums to 0."""
    w = Window.partitionBy(*TRIP_KEY)
    is_void = (
        (F.count("*").over(w) == 2)
        & (F.min("total_amount").over(w) < 0)
        & (F.abs(F.sum("total_amount").over(w)) < tolerance)
    )
    return df.withColumn("is_void", is_void)


def rejection_rules(month, quality):
    pickup, dropoff = F.col("tpep_pickup_datetime"), F.col("tpep_dropoff_datetime")
    negative = (F.col("fare_amount") < 0) | (F.col("total_amount") < 0)
    return [
        ("pickup_outside_file_month", F.date_format(pickup, "yyyy-MM") != month),
        ("dropoff_before_pickup", dropoff < pickup),
        ("duration_over_limit", F.col("trip_duration_min") > quality["max_duration_h"] * 60),
        ("negative_amount", negative & ~F.col("is_void")),
    ]


def add_quality_flags(df, quality):
    return df.withColumns({
        "is_outlier": (F.col("trip_distance") > quality["max_distance_mi"]) | (F.col("fare_amount") > quality["max_fare_usd"]),
        "is_passenger_count_missing": F.coalesce(F.col("passenger_count"), F.lit(0)) == 0,
    })


def transform_trips(df, month, quality):
    """Raw trips of one file month -> (silver, quarantine)."""
    df = flag_void_pairs(add_trip_attributes(normalize_trips(df)), quality["void_tolerance_usd"])
    valid, rejected = split_by_rules(df, rejection_rules(month, quality))
    kept, duplicates = keep_first(valid.filter(~F.col("is_void")), TRIP_KEY, [F.desc("total_amount")])
    silver = add_quality_flags(kept.unionByName(valid.filter(F.col("is_void"))), quality)
    return silver, rejected.unionByName(duplicates)


def transform_zones(df):
    return snake_case_columns(df).withColumn("location_id", F.col("location_id").cast("int"))
