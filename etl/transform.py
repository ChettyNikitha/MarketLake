"""Transform stage: flatten raw Kalshi JSON pages into typed pandas
DataFrames containing only the columns needed by the Postgres schema
(db/schema.sql).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

EVENTS_COLUMNS = ["event_ticker", "series_ticker", "category", "title", "status", "strike_date"]
MARKETS_COLUMNS = [
    "ticker",
    "event_ticker",
    "title",
    "status",
    "yes_bid",
    "yes_ask",
    "no_bid",
    "no_ask",
    "last_price",
    "volume",
    "open_interest",
]


def _derive_event_status(event: Dict[str, Any]) -> Any:
    """Kalshi's event objects don't carry their own status -- only their
    nested markets do. Treat an event as "active" if any of its markets are,
    otherwise fall back to whatever status its markets report (or the
    event's own status field, for older/alternate API shapes)."""
    market_statuses = {m.get("status") for m in event.get("markets", []) if m.get("status")}
    if "active" in market_statuses:
        return "active"
    if market_statuses:
        return next(iter(market_statuses))
    return event.get("status")


def _derive_strike_date(event: Dict[str, Any]) -> Any:
    """Likewise, events don't carry a direct strike/close date in the real
    API -- use the earliest market close_time as the event's effective
    resolution date, falling back to any event-level date field."""
    close_times = [m.get("close_time") for m in event.get("markets", []) if m.get("close_time")]
    if close_times:
        return min(close_times)
    return event.get("strike_date") or event.get("start_date")


def _flatten_events(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for page in pages:
        for event in page.get("events", []):
            rows.append(
                {
                    "event_ticker": event.get("event_ticker"),
                    "series_ticker": event.get("series_ticker"),
                    "category": event.get("category"),
                    "title": event.get("title"),
                    "status": _derive_event_status(event),
                    "strike_date": _derive_strike_date(event),
                }
            )
    return rows


def _to_number(value: Any) -> float | None:
    """Kalshi returns prices/volume as decimal strings (e.g. "0.5500" for
    yes_bid_dollars, "1730.18" for volume_fp) rather than plain numbers."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _flatten_markets(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for page in pages:
        for market in page.get("markets", []):
            rows.append(
                {
                    "ticker": market.get("ticker"),
                    "event_ticker": market.get("event_ticker"),
                    "title": market.get("title"),
                    "status": market.get("status"),
                    "yes_bid": _to_number(market.get("yes_bid_dollars")),
                    "yes_ask": _to_number(market.get("yes_ask_dollars")),
                    "no_bid": _to_number(market.get("no_bid_dollars")),
                    "no_ask": _to_number(market.get("no_ask_dollars")),
                    "last_price": _to_number(market.get("last_price_dollars")),
                    "volume": _to_number(market.get("volume_fp")),
                    "open_interest": _to_number(market.get("open_interest_fp")),
                }
            )
    return rows


def transform_events(pages: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = _flatten_events(pages)
    df = pd.DataFrame(rows, columns=EVENTS_COLUMNS)
    if not df.empty:
        df = df.dropna(subset=["event_ticker"]).drop_duplicates(subset=["event_ticker"])
        df["strike_date"] = pd.to_datetime(df["strike_date"], utc=True, errors="coerce")
        for col in ("event_ticker", "series_ticker", "category", "title", "status"):
            df[col] = df[col].astype("string")
    return df


def transform_markets(pages: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = _flatten_markets(pages)
    df = pd.DataFrame(rows, columns=MARKETS_COLUMNS)
    if not df.empty:
        df = df.dropna(subset=["ticker"]).drop_duplicates(subset=["ticker"])
        for col in ("ticker", "event_ticker", "title", "status"):
            df[col] = df[col].astype("string")
        for col in ("yes_bid", "yes_ask", "no_bid", "no_ask", "last_price", "volume", "open_interest"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
    return df


def transform(event_pages: List[Dict[str, Any]], market_pages: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    events_df = transform_events(event_pages)
    markets_df = transform_markets(market_pages)
    return events_df, markets_df
