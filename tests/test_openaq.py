from notebook_loader import load_libs

lib = load_libs("nb_lib_common", "nb_lib_openaq")

SCHEMA = "location_id int, sensor_id int, parameter string, period_start_local string, value double, percent_complete double"
ROWS = [
    (384, 673, "pm25", "2024-03-10T00:00:00-05:00", 11.8, 100.0),  # DST day: local date must stay 03-10
    (384, 673, "pm25", "2024-03-11T00:00:00-04:00", 9.0, 50.0),    # low coverage
    (384, 673, "pm25", "2024-03-12T00:00:00-04:00", None, 0.0),    # null value
    (384, 673, "pm25", "2024-03-11T00:00:00-04:00", 9.0, 40.0),    # duplicate of 03-11
]


def test_air_quality(spark, config):
    df = spark.createDataFrame(ROWS, SCHEMA)
    silver, quarantine = lib.transform_air_quality(df, config["openaq"]["min_coverage_pct"])
    days = {r.date.isoformat(): r for r in silver.collect()}
    assert sorted(days) == ["2024-03-10", "2024-03-11"]
    assert days["2024-03-11"].is_low_coverage and days["2024-03-11"].percent_complete == 50.0
    assert not days["2024-03-10"].is_low_coverage
    assert sorted(r.reject_reason for r in quarantine.collect()) == ["duplicate", "value_null"]


def test_monitor_zones_types(spark):
    df = spark.createDataFrame([("857", "Fort Lee", "40.85", "-73.96", None, None, "Outside NYC")],
                               "location_id string, location_name string, latitude string, longitude string, zone_id string, zone string, borough string")
    row = lib.transform_monitor_zones(df).first()
    assert (row.location_id, row.zone_id, row.borough) == (857, None, "Outside NYC")
