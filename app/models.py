"""SQLAlchemy ORM models mirroring db/schema.sql.

These models are used for reads via the FastAPI routers. Writes (upserts)
from the ETL pipeline go through raw SQL in etl/load.py instead, to
demonstrate explicit INSERT ... ON CONFLICT DO UPDATE SQL.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import relationship

from app.db import Base


class Event(Base):
    __tablename__ = "events"

    event_ticker = Column(Text, primary_key=True)
    series_ticker = Column(Text)
    category = Column(Text, index=True)
    title = Column(Text)
    status = Column(Text)
    strike_date = Column(DateTime(timezone=True))
    loaded_at = Column(DateTime(timezone=True))

    markets = relationship("Market", back_populates="event")


class Market(Base):
    __tablename__ = "markets"

    ticker = Column(Text, primary_key=True)
    event_ticker = Column(Text, ForeignKey("events.event_ticker"), index=True)
    title = Column(Text)
    status = Column(Text, index=True)
    yes_bid = Column(Numeric(12, 4))
    yes_ask = Column(Numeric(12, 4))
    no_bid = Column(Numeric(12, 4))
    no_ask = Column(Numeric(12, 4))
    last_price = Column(Numeric(12, 4))
    volume = Column(Numeric(18, 4))
    open_interest = Column(Numeric(18, 4))
    loaded_at = Column(DateTime(timezone=True))

    event = relationship("Event", back_populates="markets")


class EtlRun(Base):
    """One row per etl.pipeline.run_pipeline() invocation -- backs the
    operator dashboard's "last run" / throughput panel.
    """

    __tablename__ = "etl_runs"

    run_id = Column(Text, primary_key=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Numeric(10, 3))
    status = Column(Text, nullable=False, default="running")
    events_extracted = Column(Integer)
    markets_extracted = Column(Integer)
    events_loaded = Column(Integer)
    markets_loaded = Column(Integer)
    error_message = Column(Text)
