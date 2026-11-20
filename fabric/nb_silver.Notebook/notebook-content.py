# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "d09c7e6f-8019-4094-b646-005b9957c284",
# META       "default_lakehouse_name": "lh_bronze",
# META       "default_lakehouse_workspace_id": "6e107ded-9300-4274-a3af-9ca212441d27",
# META       "known_lakehouses": [
# META         {
# META           "id": "d09c7e6f-8019-4094-b646-005b9957c284"
# META         },
# META         {
# META           "id": "7ff47524-a1b9-43c0-bb65-1d1b207fc606"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

%run nb_lib_common

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run nb_lib_taxi

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run nb_lib_openaq

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run nb_lib_worldbank

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run nb_lib_ecb

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Silver layer: Bronze (default lakehouse lh_bronze) -> lh_silver tables. Full reload on every run.
# Every Bronze row ends in exactly one place: a silver table or its quarantine table (with reject_reason).
import json
from functools import reduce

from pyspark.sql import functions as F

CONFIG_PATH = "Files/config/sources.json"  # bootstrap literal: pl_ingest copies the config here

cfg = json.loads(spark.read.text(CONFIG_PATH, wholetext=True).first().value)
BRONZE, SILVER = cfg["lakehouses"]["bronze"], cfg["lakehouses"]["silver"]


def bronze_file(folder, path):
    """Files/<folder>/<file name of the source path>, the place pl_ingest wrote the file to."""
    return f"Files/{folder}/{path.rsplit('/', 1)[-1]}"


def bronze_table(source):
    return spark.read.table(f"{BRONZE}.{source['bronze_table']}")


def save(df, table):
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{SILVER}.{table}")
    rows = spark.read.table(f"{SILVER}.{table}").count()
    print(f"{table}: {rows:,} rows")
    return rows


def save_split(source, silver, quarantine, bronze_rows):
    """Write silver + quarantine and prove that no row was lost or duplicated."""
    total = save(silver, source["silver_table"]) + save(quarantine, source["quarantine_table"])
    assert total == bronze_rows, f"{source['silver_table']}: bronze {bronze_rows:,} != silver + quarantine {total:,}"


def union_all(dfs):
    return reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), dfs)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Taxi trips: one file per month; the month is needed by the pickup_outside_file_month rule.
taxi = cfg["taxi"]
silver_parts, quarantine_parts, bronze_rows = [], [], 0
for month in taxi["months"]:
    raw = spark.read.parquet(bronze_file(taxi["bronze_folder"], taxi["path_template"].format(month=month))).select(
        "*",
        F.col("_metadata.file_path").alias("source_file"),
        F.col("_metadata.file_modification_time").alias("load_ts"),
    )
    bronze_rows += raw.count()
    silver, quarantine = transform_trips(raw, month, taxi["quality"])
    silver_parts.append(silver)
    quarantine_parts.append(quarantine)

save_split(taxi, union_all(silver_parts), union_all(quarantine_parts), bronze_rows)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Taxi zone lookup (reference data, no rejection rules).
zones = cfg["taxi_zones"]
raw = spark.read.option("header", True).csv(bronze_file(zones["bronze_folder"], zones["path"]))
save(transform_zones(raw), zones["silver_table"])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# OpenAQ daily values per sensor.
openaq = cfg["openaq"]
raw = bronze_table(openaq)
save_split(openaq, *transform_air_quality(raw, openaq["min_coverage_pct"]), raw.count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Monitor -> taxi zone mapping (made by scripts/map_monitors_to_zones.py).
monitors = cfg["monitor_zones"]
raw = spark.read.option("header", True).csv(bronze_file(monitors["bronze_folder"], monitors["path"]))
save(transform_monitor_zones(raw), monitors["silver_table"])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# World Bank yearly GDP.
worldbank = cfg["worldbank"]
raw = bronze_table(worldbank)
save_split(worldbank, *transform_gdp(raw), raw.count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ECB USD per EUR. Silver is a full calendar (missing days filled), so its row count differs from Bronze.
ecb = cfg["ecb"]
fx, rejected = transform_fx(bronze_table(ecb), ecb["missing_day_rule"])
save(fx, ecb["silver_table"])
save(rejected, ecb["quarantine_table"])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
