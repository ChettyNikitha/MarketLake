"""Orchestrates extract -> transform -> load with structured logging."""
from __future__ import annotations

import datetime as dt
import logging
import time
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings
from etl.extract import run_extract
from etl.load import load, record_etl_run
from etl.transform import transform

logger = logging.getLogger("etl.pipeline")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def run_pipeline(
    settings: Optional[Settings] = None,
    engine: Optional[Engine] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    settings = settings or get_settings()
    run_id = uuid.uuid4().hex[:12]
    dt_str = dt.date.today().isoformat()
    started_at = dt.datetime.now(dt.timezone.utc)
    started = time.monotonic()

    logger.info("run_id=%s event=pipeline_start dry_run=%s", run_id, dry_run)

    engine = engine or create_engine(settings.database_url, future=True)
    if not dry_run:
        record_etl_run(engine, run_id=run_id, started_at=started_at, status="running")

    try:
        extracted = run_extract(run_id=run_id, dt_str=dt_str, settings=settings)
        logger.info(
            "run_id=%s event=extract_complete event_pages=%d market_pages=%d",
            run_id,
            len(extracted["event_pages"]),
            len(extracted["market_pages"]),
        )

        events_df, markets_df = transform(extracted["event_pages"], extracted["market_pages"])
        logger.info(
            "run_id=%s event=transform_complete events=%d markets=%d",
            run_id,
            len(events_df),
            len(markets_df),
        )

        load_result = load(
            events_df=events_df,
            markets_df=markets_df,
            engine=engine,
            data_lake_root=settings.data_lake_root,
            dt_str=dt_str,
            dry_run=dry_run,
        )
        logger.info(
            "run_id=%s event=load_complete events_loaded=%d markets_loaded=%d",
            run_id,
            load_result["events_loaded"],
            load_result["markets_loaded"],
        )
    except Exception as exc:
        if not dry_run:
            record_etl_run(
                engine,
                run_id=run_id,
                started_at=started_at,
                status="failed",
                finished_at=dt.datetime.now(dt.timezone.utc),
                duration_seconds=round(time.monotonic() - started, 3),
                error_message=str(exc)[:2000],
            )
        logger.exception("run_id=%s event=pipeline_failed", run_id)
        raise

    duration_seconds = round(time.monotonic() - started, 3)
    summary = {
        "run_id": run_id,
        "dt": dt_str,
        "dry_run": dry_run,
        "duration_seconds": duration_seconds,
        "raw_files": extracted["event_files"] + extracted["market_files"],
        "events_extracted": len(events_df),
        "markets_extracted": len(markets_df),
        **load_result,
    }

    if not dry_run:
        record_etl_run(
            engine,
            run_id=run_id,
            started_at=started_at,
            status="success",
            finished_at=dt.datetime.now(dt.timezone.utc),
            duration_seconds=duration_seconds,
            events_extracted=summary["events_extracted"],
            markets_extracted=summary["markets_extracted"],
            events_loaded=summary["events_loaded"],
            markets_loaded=summary["markets_loaded"],
        )

    logger.info("run_id=%s event=pipeline_complete duration_seconds=%.3f", run_id, duration_seconds)
    return summary
