import json

import pytest
from pyspark.sql import SparkSession

from notebook_loader import ROOT


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def config():
    return json.loads((ROOT / "config" / "sources.json").read_text())
