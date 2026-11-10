"""Local exploration of one taxi month. Produces the counts in docs/data_profile.md.

Usage: python scripts/profile_taxi.py 2024-01   (file must be in data/)
"""
import json
import sys

from pyspark.sql import SparkSession, Window, functions as F

KEY = ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID"]


def anomaly_checks(month_start, month_end):
    pu, do = F.col("tpep_pickup_datetime"), F.col("tpep_dropoff_datetime")
    minutes = (F.unix_timestamp(do) - F.unix_timestamp(pu)) / 60
    return {
        "pickup_before_month": pu < month_start,
        "pickup_after_month": pu >= month_end,
        "dropoff_before_pickup": do < pu,
        "duration_zero": do == pu,
        "duration_over_24h": minutes > 24 * 60,
        "passenger_null": F.col("passenger_count").isNull(),
        "passenger_zero": F.col("passenger_count") == 0,
        "distance_zero": F.col("trip_distance") == 0,
        "distance_over_100mi": F.col("trip_distance") > 100,
        "fare_negative": F.col("fare_amount") < 0,
        "total_negative": F.col("total_amount") < 0,
        "fare_over_1000": F.col("fare_amount") > 1000,
        "pu_unknown_zone": F.col("PULocationID").isin(264, 265),
    }


def main(month):
    spark = SparkSession.builder.master("local[*]").config("spark.ui.showConsoleProgress", "false").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    cfg = json.load(open("config/sources.json"))
    file_name = cfg["taxi"]["url_template"].format(month=month).rsplit("/", 1)[1]
    df = spark.read.parquet(f"data/{file_name}").cache()

    start = F.to_timestamp(F.lit(f"{month}-01"))
    end = F.add_months(start, 1).cast("timestamp")
    checks = anomaly_checks(start.cast("timestamp_ntz"), end.cast("timestamp_ntz"))

    print("rows:", df.count())
    df.select([F.sum(c.cast("int")).alias(k) for k, c in checks.items()]).show(vertical=True)

    groups = df.withColumn("n", F.count("*").over(Window.partitionBy(*KEY))).filter("n > 1")
    has_negative = groups.groupBy(*KEY).agg((F.min("total_amount") < 0).alias("neg"))
    has_negative.groupBy("neg").count().show()  # neg=true: void pairs, neg=false: true duplicates

    df.groupBy(F.to_date("tpep_pickup_datetime").alias("day")).count().orderBy("day").show(40)


if __name__ == "__main__":
    main(sys.argv[1])
