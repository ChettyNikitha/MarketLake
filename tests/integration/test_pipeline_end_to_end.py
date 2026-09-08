"""Integration test: mocks only the Kalshi HTTP layer, runs the real
etl.pipeline.run_pipeline() against a test Postgres + temp data_lake dir, and
asserts raw JSON + curated Parquet files were written and DB rows exist.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import text

from etl.pipeline import run_pipeline
from tests.integration.test_api_events import _apply_schema, _clear_tables


@pytest.fixture
def pipeline_settings(tmp_path, test_database_url, rsa_private_key_pem):
    from app.config import Settings

    return Settings(
        kalshi_key_id="test-key-id",
        kalshi_private_key_pem=rsa_private_key_pem,
        kalshi_base_url="https://demo-api.kalshi.co",
        database_url=test_database_url,
        data_lake_root=str(tmp_path),
    )


def test_pipeline_end_to_end(monkeypatch, test_engine, pipeline_settings, sample_events_json):
    _apply_schema(test_engine)
    _clear_tables(test_engine)

    from etl.kalshi_client import KalshiClient

    # sample_events_json already carries each market nested under its event
    # (Kalshi's with_nested_markets=true shape); the markets raw partition is
    # derived from that by etl.extract, no separate client call needed.
    monkeypatch.setattr(
        KalshiClient,
        "get_events_pages",
        lambda self, params=None, max_pages=None: iter([sample_events_json]),
    )

    summary = run_pipeline(settings=pipeline_settings, engine=test_engine, dry_run=False)

    assert summary["events_extracted"] == 3
    assert summary["markets_extracted"] == 3
    assert summary["events_loaded"] == 3
    assert summary["markets_loaded"] == 3

    dt_str = dt.date.today().isoformat()

    raw_events_dir = Path(pipeline_settings.data_lake_root) / "raw" / "events" / f"dt={dt_str}"
    raw_markets_dir = Path(pipeline_settings.data_lake_root) / "raw" / "markets" / f"dt={dt_str}"
    assert any(raw_events_dir.glob("*.json"))
    assert any(raw_markets_dir.glob("*.json"))

    curated_events = Path(pipeline_settings.data_lake_root) / "curated" / "events" / f"dt={dt_str}" / "events.parquet"
    curated_markets = Path(pipeline_settings.data_lake_root) / "curated" / "markets" / f"dt={dt_str}" / "markets.parquet"
    assert curated_events.exists()
    assert curated_markets.exists()

    with test_engine.connect() as conn:
        event_count = conn.execute(text("SELECT COUNT(*) FROM events")).scalar_one()
        market_count = conn.execute(text("SELECT COUNT(*) FROM markets")).scalar_one()
    assert event_count == 3
    assert market_count == 3

    _clear_tables(test_engine)
