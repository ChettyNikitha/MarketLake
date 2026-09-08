"""OPTIONAL stretch module: re-implements the events/markets flattening logic
using PySpark DataFrames instead of pandas.

This module is NOT wired into etl/pipeline.py and is NOT a dependency of
requirements.txt -- it is a design artifact showing how the same transform
step would look on a Spark-based stack. Install it with:

    pip install -r requirements-optional.txt

and run interactively / adapt into a job runner as needed.
"""
from typing import Any, Dict, List, Tuple

try:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import (
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    PYSPARK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PYSPARK_AVAILABLE = False


EVENTS_SCHEMA = None
MARKETS_SCHEMA = None

if PYSPARK_AVAILABLE:
    EVENTS_SCHEMA = StructType(
        [
            StructField("event_ticker", StringType(), True),
            StructField("series_ticker", StringType(), True),
            StructField("category", StringType(), True),
            StructField("title", StringType(), True),
            StructField("status", StringType(), True),
            StructField("strike_date", TimestampType(), True),
        ]
    )

    MARKETS_SCHEMA = StructType(
        [
            StructField("ticker", StringType(), True),
            StructField("event_ticker", StringType(), True),
            StructField("title", StringType(), True),
            StructField("status", StringType(), True),
            StructField("yes_bid", LongType(), True),
            StructField("yes_ask", LongType(), True),
            StructField("no_bid", LongType(), True),
            StructField("no_ask", LongType(), True),
            StructField("last_price", LongType(), True),
            StructField("volume", LongType(), True),
            StructField("open_interest", LongType(), True),
        ]
    )


def transform_events_spark(spark: "SparkSession", pages: List[Dict[str, Any]]) -> "DataFrame":
    """Flatten raw event pages into a Spark DataFrame with the same shape as
    etl.transform.transform_events's pandas output.
    """
    if not PYSPARK_AVAILABLE:
        raise ImportError("pyspark is not installed; see requirements-optional.txt")

    rows = []
    for page in pages:
        for event in page.get("events", []):
            rows.append(
                (
                    event.get("event_ticker"),
                    event.get("series_ticker"),
                    event.get("category"),
                    event.get("title"),
                    event.get("status"),
                    event.get("strike_date") or event.get("start_date"),
                )
            )
    return spark.createDataFrame(rows, schema=EVENTS_SCHEMA).dropDuplicates(["event_ticker"])


def transform_markets_spark(spark: "SparkSession", pages: List[Dict[str, Any]]) -> "DataFrame":
    if not PYSPARK_AVAILABLE:
        raise ImportError("pyspark is not installed; see requirements-optional.txt")

    rows = []
    for page in pages:
        for market in page.get("markets", []):
            rows.append(
                (
                    market.get("ticker"),
                    market.get("event_ticker"),
                    market.get("title"),
                    market.get("status"),
                    market.get("yes_bid"),
                    market.get("yes_ask"),
                    market.get("no_bid"),
                    market.get("no_ask"),
                    market.get("last_price"),
                    market.get("volume"),
                    market.get("open_interest"),
                )
            )
    return spark.createDataFrame(rows, schema=MARKETS_SCHEMA).dropDuplicates(["ticker"])


def transform_spark(
    spark: "SparkSession", event_pages: List[Dict[str, Any]], market_pages: List[Dict[str, Any]]
) -> Tuple["DataFrame", "DataFrame"]:
    return transform_events_spark(spark, event_pages), transform_markets_spark(spark, market_pages)
