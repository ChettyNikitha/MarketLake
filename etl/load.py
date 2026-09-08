"""Load stage:
  (a) write curated DataFrames to Parquet in the data lake, partitioned by dt
  (b) upsert DataFrames into Postgres using explicit INSERT ... ON CONFLICT
      DO UPDATE SQL (not ORM merge()), so re-running the pipeline is
      idempotent and never creates duplicate rows.
"""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("etl.load")

ETL_RUN_UPSERT_SQL = text(
    """
    INSERT INTO etl_runs (
        run_id, started_at, finished_at, duration_seconds, status,
        events_extracted, markets_extracted, events_loaded, markets_loaded, error_message
    )
    VALUES (
        :run_id, :started_at, :finished_at, :duration_seconds, :status,
        :events_extracted, :markets_extracted, :events_loaded, :markets_loaded, :error_message
    )
    ON CONFLICT (run_id) DO UPDATE SET
        finished_at = EXCLUDED.finished_at,
        duration_seconds = EXCLUDED.duration_seconds,
        status = EXCLUDED.status,
        events_extracted = EXCLUDED.events_extracted,
        markets_extracted = EXCLUDED.markets_extracted,
        events_loaded = EXCLUDED.events_loaded,
        markets_loaded = EXCLUDED.markets_loaded,
        error_message = EXCLUDED.error_message
    """
)


def record_etl_run(
    engine: Engine,
    run_id: str,
    started_at: dt.datetime,
    status: str,
    finished_at: Optional[dt.datetime] = None,
    duration_seconds: Optional[float] = None,
    events_extracted: Optional[int] = None,
    markets_extracted: Optional[int] = None,
    events_loaded: Optional[int] = None,
    markets_loaded: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    """Record (or update) one row in etl_runs -- backs the dashboard's "last
    run" panel. Called once when a run starts (status="running") and again
    when it finishes (status="success"/"failed"), so an in-progress or
    crashed run is still visible rather than silently missing.
    """
    with engine.begin() as conn:
        conn.execute(
            ETL_RUN_UPSERT_SQL,
            {
                "run_id": run_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": duration_seconds,
                "status": status,
                "events_extracted": events_extracted,
                "markets_extracted": markets_extracted,
                "events_loaded": events_loaded,
                "markets_loaded": markets_loaded,
                "error_message": error_message,
            },
        )

EVENTS_UPSERT_SQL = text(
    """
    INSERT INTO events (event_ticker, series_ticker, category, title, status, strike_date, loaded_at)
    VALUES (:event_ticker, :series_ticker, :category, :title, :status, :strike_date, :loaded_at)
    ON CONFLICT (event_ticker) DO UPDATE SET
        series_ticker = EXCLUDED.series_ticker,
        category = EXCLUDED.category,
        title = EXCLUDED.title,
        status = EXCLUDED.status,
        strike_date = EXCLUDED.strike_date,
        loaded_at = EXCLUDED.loaded_at
    """
)

MARKETS_UPSERT_SQL = text(
    """
    INSERT INTO markets (
        ticker, event_ticker, title, status, yes_bid, yes_ask, no_bid, no_ask,
        last_price, volume, open_interest, loaded_at
    )
    VALUES (
        :ticker, :event_ticker, :title, :status, :yes_bid, :yes_ask, :no_bid, :no_ask,
        :last_price, :volume, :open_interest, :loaded_at
    )
    ON CONFLICT (ticker) DO UPDATE SET
        event_ticker = EXCLUDED.event_ticker,
        title = EXCLUDED.title,
        status = EXCLUDED.status,
        yes_bid = EXCLUDED.yes_bid,
        yes_ask = EXCLUDED.yes_ask,
        no_bid = EXCLUDED.no_bid,
        no_ask = EXCLUDED.no_ask,
        last_price = EXCLUDED.last_price,
        volume = EXCLUDED.volume,
        open_interest = EXCLUDED.open_interest,
        loaded_at = EXCLUDED.loaded_at
    """
)


def write_curated_parquet(df: pd.DataFrame, resource: str, dt_str: str, data_lake_root: str) -> str:
    out_dir = Path(data_lake_root) / "curated" / resource / f"dt={dt_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{resource}.parquet"
    df.to_parquet(file_path, engine="pyarrow", index=False)
    return str(file_path)


def _records_with_loaded_at(df: pd.DataFrame, loaded_at: dt.datetime) -> List[Dict[str, Any]]:
    records = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    for record in records:
        record["loaded_at"] = loaded_at
    return records


def upsert_events(engine: Engine, events_df: pd.DataFrame, loaded_at: dt.datetime) -> int:
    if events_df.empty:
        return 0
    records = _records_with_loaded_at(events_df, loaded_at)
    with engine.begin() as conn:
        conn.execute(EVENTS_UPSERT_SQL, records)
    return len(records)


def _filter_markets_with_known_event(engine: Engine, markets_df: pd.DataFrame) -> pd.DataFrame:
    """Drop markets whose event_ticker isn't (yet) present in the events
    table. Events and markets are paginated independently against Kalshi, so
    under a page cap a batch of markets can reference events outside this
    run's event page window; the `markets.event_ticker` foreign key would
    otherwise reject the whole batch. Skipped markets are picked up on a
    later run once their event has been loaded.
    """
    if markets_df.empty:
        return markets_df
    with engine.connect() as conn:
        known_event_tickers = {row[0] for row in conn.execute(text("SELECT event_ticker FROM events"))}
    known_mask = markets_df["event_ticker"].isin(known_event_tickers)
    skipped = int((~known_mask).sum())
    if skipped:
        logger.warning(
            "event=markets_skipped_unknown_event count=%d reason=event_ticker_not_yet_loaded",
            skipped,
        )
    return markets_df[known_mask]


def upsert_markets(engine: Engine, markets_df: pd.DataFrame, loaded_at: dt.datetime) -> int:
    markets_df = _filter_markets_with_known_event(engine, markets_df)
    if markets_df.empty:
        return 0
    records = _records_with_loaded_at(markets_df, loaded_at)
    with engine.begin() as conn:
        conn.execute(MARKETS_UPSERT_SQL, records)
    return len(records)


def load(
    events_df: pd.DataFrame,
    markets_df: pd.DataFrame,
    engine: Engine,
    data_lake_root: str,
    dt_str: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    loaded_at = dt.datetime.now(dt.timezone.utc)

    events_parquet = write_curated_parquet(events_df, "events", dt_str, data_lake_root)
    markets_parquet = write_curated_parquet(markets_df, "markets", dt_str, data_lake_root)

    events_loaded = 0
    markets_loaded = 0
    if not dry_run:
        events_loaded = upsert_events(engine, events_df, loaded_at)
        markets_loaded = upsert_markets(engine, markets_df, loaded_at)

    return {
        "events_parquet": events_parquet,
        "markets_parquet": markets_parquet,
        "events_loaded": events_loaded,
        "markets_loaded": markets_loaded,
    }
