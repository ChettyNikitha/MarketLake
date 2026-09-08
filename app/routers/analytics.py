"""Analytics endpoints backed by hand-written SQL (see db/analytics_queries.sql).

These demonstrate using a CTE + window function directly via SQLAlchemy Core,
rather than expressing the ranking logic in the ORM.
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TopMarketOut

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Parameterized version of analytics_queries.sql query (1): rank markets by
# volume within each event using RANK() OVER (PARTITION BY ... ORDER BY ...),
# then return the top N rows overall.
TOP_MARKETS_BY_VOLUME_SQL = text(
    """
    WITH ranked_markets AS (
        SELECT
            m.ticker,
            m.event_ticker,
            m.title,
            m.volume,
            RANK() OVER (PARTITION BY m.event_ticker ORDER BY m.volume DESC) AS rank_in_event
        FROM markets m
    )
    SELECT ticker, event_ticker, title, volume, rank_in_event
    FROM ranked_markets
    ORDER BY volume DESC NULLS LAST
    LIMIT :limit
    """
)


@router.get("/top-markets-by-volume", response_model=List[TopMarketOut])
def top_markets_by_volume(
    limit: int = Query(10, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[TopMarketOut]:
    rows = db.execute(TOP_MARKETS_BY_VOLUME_SQL, {"limit": limit}).mappings().all()
    return [TopMarketOut(**row) for row in rows]
