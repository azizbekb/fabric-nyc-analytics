# Silver transform for World Bank yearly GDP. Needs nb_lib_common.
from pyspark.sql import functions as F


def transform_gdp(df):
    """Bronze rows (country_code, indicator_id, year as text, value) -> (silver, quarantine)."""
    df = df.withColumns({"year": F.col("year").cast("int"), "gdp_usd": F.col("value").cast("double")}).drop("value")
    valid, rejected = split_by_rules(df, [("value_null", F.col("gdp_usd").isNull())])
    kept, duplicates = keep_first(valid, ["country_code", "indicator_id", "year"], [F.desc("gdp_usd")])
    return kept, rejected.unionByName(duplicates)
