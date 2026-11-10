import pytest

from notebook_loader import load_libs

wb = load_libs("nb_lib_common", "nb_lib_worldbank")
ecb = load_libs("nb_lib_common", "nb_lib_ecb")


def test_gdp(spark):
    df = spark.createDataFrame(
        [("USA", "NY.GDP.MKTP.CD", "2024", 2.9e13), ("USA", "NY.GDP.MKTP.CD", "2026", None)],
        "country_code string, indicator_id string, year string, value double",
    )
    silver, quarantine = wb.transform_gdp(df)
    assert [(r.year, r.gdp_usd) for r in silver.collect()] == [(2024, 2.9e13)]
    assert [(r.year, r.reject_reason) for r in quarantine.collect()] == [(2026, "value_null")]


def test_fx_weekend_takes_last_available_rate(spark, config):
    # Friday 2023-12-29 has a rate; Sat, Sun and the 01-01 holiday do not.
    df = spark.createDataFrame([("2023-12-29", "1.1050"), ("2024-01-02", "1.0956")], "TIME_PERIOD string, OBS_VALUE string")
    silver, quarantine = ecb.transform_fx(df, config["ecb"]["missing_day_rule"])
    rows = [(r.date.isoformat(), r.usd_per_eur, r.is_filled) for r in silver.orderBy("date").collect()]
    assert rows == [
        ("2023-12-29", 1.105, False),
        ("2023-12-30", 1.105, True),
        ("2023-12-31", 1.105, True),
        ("2024-01-01", 1.105, True),
        ("2024-01-02", 1.0956, False),
    ]
    assert quarantine.count() == 0


def test_fx_unknown_rule_fails(spark):
    df = spark.createDataFrame([("2024-01-02", "1.0956")], "TIME_PERIOD string, OBS_VALUE string")
    with pytest.raises(ValueError):
        ecb.transform_fx(df, "linear")
