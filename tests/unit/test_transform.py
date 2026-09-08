"""Unit tests for etl/transform.py -- flattening logic against fixture JSON."""
import pandas as pd

from etl.transform import EVENTS_COLUMNS, MARKETS_COLUMNS, transform, transform_events, transform_markets


def test_transform_events_shape_and_columns(sample_events_json):
    df = transform_events([sample_events_json])

    assert list(df.columns) == EVENTS_COLUMNS
    assert len(df) == 3
    assert set(df["event_ticker"]) == {
        "KXCRICKET-26MAR01",
        "KXCRICKET-26MAR05",
        "KXFED-26MAR18",
    }
    assert pd.api.types.is_datetime64_any_dtype(df["strike_date"])


def test_transform_events_drops_duplicates(sample_events_json):
    df = transform_events([sample_events_json, sample_events_json])
    assert len(df) == 3


def test_transform_markets_shape_and_columns(sample_markets_json):
    df = transform_markets([sample_markets_json])

    assert list(df.columns) == MARKETS_COLUMNS
    assert len(df) == 3
    row = df[df["ticker"] == "KXCRICKET-26MAR01-MI"].iloc[0]
    assert row["yes_bid"] == 0.55
    assert row["volume"] == 12000.0
    assert row["event_ticker"] == "KXCRICKET-26MAR01"


def test_transform_markets_numeric_dtypes(sample_markets_json):
    df = transform_markets([sample_markets_json])
    for col in ("yes_bid", "yes_ask", "no_bid", "no_ask", "last_price", "volume", "open_interest"):
        assert str(df[col].dtype) == "Float64"


def test_transform_combines_events_and_markets(sample_events_json, sample_markets_json):
    events_df, markets_df = transform([sample_events_json], [sample_markets_json])
    assert len(events_df) == 3
    assert len(markets_df) == 3


def test_transform_handles_empty_pages():
    events_df = transform_events([])
    markets_df = transform_markets([])
    assert events_df.empty
    assert markets_df.empty
    assert list(events_df.columns) == EVENTS_COLUMNS
    assert list(markets_df.columns) == MARKETS_COLUMNS
