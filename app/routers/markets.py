from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Market
from app.schemas import MarketOut

router = APIRouter(prefix="/api/markets", tags=["markets"])


@router.get("", response_model=List[MarketOut])
def list_markets(
    event_ticker: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Market]:
    query = db.query(Market)
    if event_ticker:
        query = query.filter(Market.event_ticker == event_ticker)
    if status:
        query = query.filter(Market.status == status)
    return query.order_by(Market.ticker).offset(offset).limit(limit).all()


@router.get("/{ticker}", response_model=MarketOut)
def get_market(ticker: str, db: Session = Depends(get_db)) -> Market:
    market = db.query(Market).filter(Market.ticker == ticker).first()
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return market
