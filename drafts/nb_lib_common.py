# Shared Silver helpers. Pure functions only: no Spark session, no notebookutils, nothing runs on import.
import re

from pyspark.sql import Window, functions as F


def to_snake_case(name):
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return name.lower()


def snake_case_columns(df):
    return df.toDF(*[to_snake_case(c) for c in df.columns])


def split_by_rules(df, rules):
    """rules: ordered list of (reason, condition). The first matching reason wins.
    Returns (valid, rejected); rejected rows carry reject_reason. No row is lost."""
    reason = F.coalesce(*[F.when(condition, F.lit(r)) for r, condition in rules])
    tagged = df.withColumn("reject_reason", reason)
    valid = tagged.filter(F.col("reject_reason").isNull()).drop("reject_reason")
    return valid, tagged.filter(F.col("reject_reason").isNotNull())


def keep_first(df, keys, order_by):
    """Keep the first row per key; the other rows are returned with reject_reason = 'duplicate'."""
    ranked = df.withColumn("_rn", F.row_number().over(Window.partitionBy(*keys).orderBy(*order_by)))
    kept = ranked.filter("_rn = 1").drop("_rn")
    duplicates = ranked.filter("_rn > 1").drop("_rn").withColumn("reject_reason", F.lit("duplicate"))
    return kept, duplicates
