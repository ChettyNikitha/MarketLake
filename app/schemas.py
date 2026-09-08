"""Pydantic response models for the API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_ticker: str
    series_ticker: Optional[str] = None
    category: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    strike_date: Optional[datetime] = None
    loaded_at: Optional[datetime] = None


class MarketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    event_ticker: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    yes_bid: Optional[float] = None
    yes_ask: Optional[float] = None
    no_bid: Optional[float] = None
    no_ask: Optional[float] = None
    last_price: Optional[float] = None
    volume: Optional[float] = None
    open_interest: Optional[float] = None
    loaded_at: Optional[datetime] = None


class TopMarketOut(BaseModel):
    ticker: str
    event_ticker: Optional[str] = None
    title: Optional[str] = None
    volume: Optional[float] = None
    rank_in_event: Optional[int] = None


class HealthOut(BaseModel):
    status: str
    database: str
