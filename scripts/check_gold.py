"""Local prototype of the Gold taxi aggregation (mirrors dbo.load_fact_taxi_daily) on one month, with checks.

Usage: python scripts/check_gold.py 2024-01
Needs data/<taxi file> and data/ecb_fx.csv (see README). Prints the checks; exits 1 if one fails.
"""
import json
import sys
from pathlib import Path

from pyspark.sql import SparkSession, functions as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from notebook_loader import load_libs  # noqa: E402

EDGE_DAYS = 3          # first/last days to inspect
EDGE_RATIO = (0.5, 2)  # a day outside median * ratio is treated as a fake dip/spike


def fact_taxi_daily(silver, fx):
    clean = ~F.col("is_outlier")
    daily = silver.filter(~F.col("is_void")).groupBy("pickup_date", F.col("pu_location_id").alias("zone_id")).agg(
        F.count("*").alias("trips"),
        F.sum(clean.cast("int")).alias("clean_trips"),
        F.sum("fare_amount").alias("total_fare_usd"),
        F.sum("total_amount").alias("total_amount_usd"),
        F.avg(F.when(clean, F.col("fare_amount"))).alias("avg_fare_usd"),
        F.avg(F.when(clean, F.col("trip_distance"))).alias("avg_distance_mi"),
        F.avg(F.when(clean, F.col("trip_duration_min"))).alias("avg_duration_min"),
    )
    return (daily.join(fx, daily.pickup_date == fx.date, "left")
            .withColumn("total_amount_eur", F.col("total_amount_usd") / F.col("usd_per_eur"))
            .drop("date", "is_filled"))


def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'FAIL'}] {name} {detail}")
    return ok


def main(month):
    spark = SparkSession.builder.master("local[*]").config("spark.ui.showConsoleProgress", "false").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    cfg = json.loads((ROOT / "config" / "sources.json").read_text())
    taxi = load_libs("nb_lib_common", "nb_lib_taxi")
    ecb = load_libs("nb_lib_common", "nb_lib_ecb")

    raw = spark.read.parquet(str(ROOT / "data" / cfg["taxi"]["path_template"].format(month=month).rsplit("/", 1)[1]))
    silver, _ = taxi.transform_trips(raw, month, cfg["taxi"]["quality"])
    fx, _ = ecb.transform_fx(spark.read.option("header", True).csv(str(ROOT / "data" / "ecb_fx.csv")), cfg["ecb"]["missing_day_rule"])
    silver, fx = silver.cache(), fx.cache()
    fact = fact_taxi_daily(silver, fx).cache()

    trips_silver = silver.filter(~F.col("is_void")).agg(F.count("*").alias("n"), F.sum("total_amount").alias("usd")).first()
    totals = fact.agg(F.sum("trips").alias("n"), F.sum("total_amount_usd").alias("usd")).first()
    days = fact.groupBy("pickup_date").agg(F.sum("trips").alias("trips")).orderBy("pickup_date").collect()
    median = sorted(d.trips for d in days)[len(days) // 2]
    edges = days[:EDGE_DAYS] + days[-EDGE_DAYS:]

    edge_dates = [d.pickup_date for d in edges]
    hours = dict(silver.filter(~F.col("is_void") & F.col("pickup_date").isin(edge_dates))
                 .groupBy("pickup_date").agg(F.countDistinct("pickup_hour")).collect())

    print(f"fact rows: {fact.count()}, days: {len(days)}, median trips/day: {median}")
    for d in edges:
        print(f"  {d.pickup_date}  trips={d.trips}  ratio_to_median={d.trips / median:.2f}  hours_with_trips={hours[d.pickup_date]}")

    results = [
        check("trips: fact == silver (non-void)", totals.n == trips_silver.n, f"{totals.n} vs {trips_silver.n}"),
        check("total_amount_usd: fact == silver", abs(totals.usd - trips_silver.usd) < 0.01, f"{totals.usd:,.2f} vs {trips_silver.usd:,.2f}"),
        check("grain unique (date, zone)", fact.count() == fact.select("pickup_date", "zone_id").distinct().count()),
        check("all days inside the file month", all(d.pickup_date.strftime("%Y-%m") == month for d in days)),
        check("edge days are complete (trips in all 24 hours)", all(h == 24 for h in hours.values())),
        check("no fake dip/spike on edge days", all(EDGE_RATIO[0] <= d.trips / median <= EDGE_RATIO[1] for d in edges)),
        check("every fact row has an FX rate", fact.filter(F.col("usd_per_eur").isNull()).count() == 0),
        check("clean_trips <= trips", fact.filter(F.col("clean_trips") > F.col("trips")).count() == 0),
    ]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main(sys.argv[1])
