# Silver transforms for OpenAQ daily values and the monitor -> zone reference. Needs nb_lib_common.
from pyspark.sql import functions as F


def transform_air_quality(df, min_coverage_pct):
    """Bronze daily rows -> (silver, quarantine). The date is the local NYC day from period_start_local."""
    df = df.withColumn("date", F.to_date(F.substring("period_start_local", 1, 10)))
    valid, rejected = split_by_rules(df, [
        ("value_null", F.col("value").isNull()),
        ("value_negative", F.col("value") < 0),
    ])
    kept, duplicates = keep_first(valid, ["sensor_id", "date"], [F.desc("percent_complete")])
    silver = kept.withColumn("is_low_coverage", F.coalesce(F.col("percent_complete"), F.lit(0)) < min_coverage_pct)
    return silver, rejected.unionByName(duplicates)


def transform_monitor_zones(df):
    return df.withColumns({
        "location_id": F.col("location_id").cast("int"),
        "latitude": F.col("latitude").cast("double"),
        "longitude": F.col("longitude").cast("double"),
        "zone_id": F.col("zone_id").cast("int"),
    })
