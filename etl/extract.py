"""Extract stage: pull events + markets pages from Kalshi and land them as
immutable, append-only raw JSON files in the data lake.

File layout: data_lake/raw/{events|markets}/dt=YYYY-MM-DD/<resource>_<run_id>_<page>.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.config import Settings, get_settings
from etl.kalshi_client import KalshiClient


def _raw_dir(data_lake_root: str, resource: str, dt_str: str) -> Path:
    path = Path(data_lake_root) / "raw" / resource / f"dt={dt_str}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_pages(
    pages: List[Dict[str, Any]],
    resource: str,
    run_id: str,
    dt_str: str,
    data_lake_root: str,
) -> List[str]:
    written: List[str] = []
    out_dir = _raw_dir(data_lake_root, resource, dt_str)
    for page_number, page in enumerate(pages):
        file_path = out_dir / f"{resource}_{run_id}_{page_number}.json"
        file_path.write_text(json.dumps(page, indent=2), encoding="utf-8")
        written.append(str(file_path))
    return written


def extract_events(
    client: KalshiClient,
    run_id: str,
    dt_str: str,
    settings: Settings,
    params: Dict[str, Any] | None = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    pages = list(client.get_events_pages(params=params, max_pages=settings.etl_max_pages))
    files = _write_pages(pages, "events", run_id, dt_str, settings.data_lake_root)
    return files, pages


def _markets_pages_from_event_pages(event_pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Repackage the markets nested inside each event (via
    with_nested_markets=true) into their own "markets" pages, so they still
    land in their own raw data-lake partition even though they were fetched
    as part of the events call rather than a separate paginated /markets
    call.
    """
    markets_pages: List[Dict[str, Any]] = []
    for page in event_pages:
        markets = [market for event in page.get("events", []) for market in event.get("markets", [])]
        markets_pages.append({"markets": markets})
    return markets_pages


def run_extract(run_id: str, dt_str: str, settings: Settings | None = None) -> Dict[str, Any]:
    """Extract events (with nested markets) and split out a markets raw
    partition. Returns raw file paths and in-memory pages.
    """
    settings = settings or get_settings()
    client = KalshiClient(settings=settings)

    event_files, event_pages = extract_events(client, run_id, dt_str, settings)

    market_pages = _markets_pages_from_event_pages(event_pages)
    market_files = _write_pages(market_pages, "markets", run_id, dt_str, settings.data_lake_root)

    return {
        "event_files": event_files,
        "market_files": market_files,
        "event_pages": event_pages,
        "market_pages": market_pages,
    }
