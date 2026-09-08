"""Integration tests: require a real Postgres reachable via DATABASE_URL.

Spins up the schema, loads fixture data through etl/load.py, then exercises
the FastAPI routes via TestClient. Also asserts duplicate-prevention: loading
the same fixtures twice must not double row counts (upsert, not insert).
"""
import datetime as dt

from pathlib import Path

import pytest
from sqlalchemy import text

from etl.load import upsert_events, upsert_markets
from etl.transform import transform_events, transform_markets

SCHEMA_SQL_PATH = Path(__file__).parent.parent.parent / "db" / "schema.sql"


def _apply_schema(engine):
    schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in filter(None, (s.strip() for s in schema_sql.split(";"))):
            conn.execute(text(statement))


def _clear_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM markets"))
        conn.execute(text("DELETE FROM events"))


@pytest.fixture
def loaded_engine(test_engine, sample_events_json, sample_markets_json):
    _apply_schema(test_engine)
    _clear_tables(test_engine)

    events_df = transform_events([sample_events_json])
    markets_df = transform_markets([sample_markets_json])
    loaded_at = dt.datetime.now(dt.timezone.utc)

    upsert_events(test_engine, events_df, loaded_at)
    upsert_markets(test_engine, markets_df, loaded_at)

    yield test_engine

    _clear_tables(test_engine)


def test_list_events_returns_curated_rows(client, loaded_engine):
    response = client.get("/api/events")
    assert response.status_code == 200
    tickers = {row["event_ticker"] for row in response.json()}
    assert "KXCRICKET-26MAR01" in tickers
    assert "KXFED-26MAR18" in tickers


def test_list_events_filters_by_category(client, loaded_engine):
    response = client.get("/api/events", params={"category": "Economics"})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["event_ticker"] == "KXFED-26MAR18"


def test_get_single_event(client, loaded_engine):
    response = client.get("/api/events/KXCRICKET-26MAR01")
    assert response.status_code == 200
    assert response.json()["title"].startswith("Will Mumbai Indians")


def test_get_missing_event_404(client, loaded_engine):
    response = client.get("/api/events/NOPE-DOES-NOT-EXIST")
    assert response.status_code == 404


def test_duplicate_load_does_not_double_row_counts(test_engine, sample_events_json, sample_markets_json, loaded_engine):
    with test_engine.connect() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM events")).scalar_one()

    # Re-run the same load a second time.
    events_df = transform_events([sample_events_json])
    markets_df = transform_markets([sample_markets_json])
    loaded_at = dt.datetime.now(dt.timezone.utc)
    upsert_events(test_engine, events_df, loaded_at)
    upsert_markets(test_engine, markets_df, loaded_at)

    with test_engine.connect() as conn:
        after = conn.execute(text("SELECT COUNT(*) FROM events")).scalar_one()

    assert before == after == 3
