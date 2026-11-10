# Silver transform for ECB daily USD per 1 EUR. Needs nb_lib_common.
from pyspark.sql import Window, functions as F


def fill_calendar_last_available(rates):
    """One row per calendar day; a day without a rate takes the last earlier rate (is_filled = true)."""
    days = rates.agg(F.sequence(F.min("date"), F.max("date")).alias("d")).select(F.explode("d").alias("date"))
    w = Window.orderBy("date").rowsBetween(Window.unboundedPreceding, Window.currentRow)
    return (
        days.join(rates, "date", "left")
        .withColumn("is_filled", F.col("usd_per_eur").isNull())
        .withColumn("usd_per_eur", F.last("usd_per_eur", ignorenulls=True).over(w))
    )


def transform_fx(df, missing_day_rule):
    """Raw ECB CSV columns -> (silver daily calendar, quarantine)."""
    if missing_day_rule != "last_available":
        raise ValueError(f"Unsupported missing_day_rule: {missing_day_rule}")
    rates = snake_case_columns(df).withColumns({
        "date": F.to_date("time_period"),
        "usd_per_eur": F.col("obs_value").cast("double"),
    })
    valid, rejected = split_by_rules(rates, [("value_null", F.col("usd_per_eur").isNull())])
    kept, duplicates = keep_first(valid, ["date"], [F.desc("usd_per_eur")])
    return fill_calendar_last_available(kept.select("date", "usd_per_eur")), rejected.unionByName(duplicates)
