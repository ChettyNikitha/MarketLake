"""Unit tests for etl/load.py -- verifies the upsert SQL/params without a real
database. engine.begin()/execute() is mocked.
"""
from unittest.mock import MagicMock

import pandas as pd

from etl.load import EVENTS_UPSERT_SQL, MARKETS_UPSERT_SQL, upsert_events, upsert_markets
import datetime as dt


def _mock_engine(known_event_tickers=()):
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = False

    # upsert_markets first checks which event_tickers already exist via
    # engine.connect() (see etl.load._filter_markets_with_known_event).
    read_conn = MagicMock()
    read_conn.execute.return_value = [(ticker,) for ticker in known_event_tickers]
    engine.connect.return_value.__enter__.return_value = read_conn
    engine.connect.return_value.__exit__.return_value = False

    return engine, conn


def test_upsert_events_executes_on_conflict_sql():
    engine, conn = _mock_engine()
    df = pd.DataFrame(
        [{"event_ticker": "E1", "series_ticker": "S1", "category": "Sports", "title": "T", "status": "open", "strike_date": None}]
    )

    count = upsert_events(engine, df, loaded_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))

    assert count == 1
    conn.execute.assert_called_once()
    executed_sql, executed_params = conn.execute.call_args[0]
    assert executed_sql is EVENTS_UPSERT_SQL
    assert "ON CONFLICT (event_ticker) DO UPDATE" in str(executed_sql)
    assert executed_params[0]["event_ticker"] == "E1"
    assert executed_params[0]["loaded_at"] == dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)


def test_upsert_markets_executes_on_conflict_sql():
    engine, conn = _mock_engine(known_event_tickers=["E1"])
    df = pd.DataFrame(
        [
            {
                "ticker": "M1",
                "event_ticker": "E1",
                "title": "T",
                "status": "open",
                "yes_bid": 50,
                "yes_ask": 52,
                "no_bid": 48,
                "no_ask": 50,
                "last_price": 51,
                "volume": 100,
                "open_interest": 20,
            }
        ]
    )

    count = upsert_markets(engine, df, loaded_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))

    assert count == 1
    conn.execute.assert_called_once()
    executed_sql, executed_params = conn.execute.call_args[0]
    assert executed_sql is MARKETS_UPSERT_SQL
    assert "ON CONFLICT (ticker) DO UPDATE" in str(executed_sql)
    assert executed_params[0]["ticker"] == "M1"


def test_upsert_markets_skips_rows_with_unknown_event_ticker():
    engine, conn = _mock_engine(known_event_tickers=["E1"])
    df = pd.DataFrame(
        [
            {
                "ticker": "M1",
                "event_ticker": "E1",
                "title": "T",
                "status": "open",
                "yes_bid": 50,
                "yes_ask": 52,
                "no_bid": 48,
                "no_ask": 50,
                "last_price": 51,
                "volume": 100,
                "open_interest": 20,
            },
            {
                "ticker": "M2",
                "event_ticker": "UNKNOWN-EVENT",
                "title": "T2",
                "status": "open",
                "yes_bid": 50,
                "yes_ask": 52,
                "no_bid": 48,
                "no_ask": 50,
                "last_price": 51,
                "volume": 100,
                "open_interest": 20,
            },
        ]
    )

    count = upsert_markets(engine, df, loaded_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))

    assert count == 1
    executed_params = conn.execute.call_args[0][1]
    assert [row["ticker"] for row in executed_params] == ["M1"]


def test_upsert_events_skips_execute_when_empty():
    engine, conn = _mock_engine()
    df = pd.DataFrame(columns=["event_ticker", "series_ticker", "category", "title", "status", "strike_date"])

    count = upsert_events(engine, df, loaded_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))

    assert count == 0
    conn.execute.assert_not_called()
