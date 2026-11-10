import pytest
from pyspark.sql import functions as F

from notebook_loader import load_libs

lib = load_libs("nb_lib_common")


@pytest.mark.parametrize("raw, expected", [
    ("VendorID", "vendor_id"),
    ("PULocationID", "pu_location_id"),
    ("Airport_fee", "airport_fee"),
    ("tpep_pickup_datetime", "tpep_pickup_datetime"),
    ("TIME_PERIOD", "time_period"),
])
def test_to_snake_case(raw, expected):
    assert lib.to_snake_case(raw) == expected


def test_split_by_rules_first_reason_wins_and_keeps_every_row(spark):
    df = spark.createDataFrame([(1, -5), (2, 50), (3, 5), (4, 5)], "id int, v int")
    rules = [("negative", F.col("v") < 0), ("too_big", F.col("v") > 10), ("odd", F.col("id") % 2 == 1)]
    valid, rejected = lib.split_by_rules(df, rules)
    assert [r.id for r in valid.collect()] == [4]
    assert {r.id: r.reject_reason for r in rejected.collect()} == {1: "negative", 2: "too_big", 3: "odd"}


def test_keep_first_returns_duplicates_with_reason(spark):
    df = spark.createDataFrame([("a", 1), ("a", 2), ("b", 3)], "k string, v int")
    kept, duplicates = lib.keep_first(df, ["k"], [F.desc("v")])
    assert sorted((r.k, r.v) for r in kept.collect()) == [("a", 2), ("b", 3)]
    assert [(r.k, r.v, r.reject_reason) for r in duplicates.collect()] == [("a", 1, "duplicate")]
