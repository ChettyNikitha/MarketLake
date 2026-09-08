"""HTML UI routes. These read from Postgres via the same DB session used by
the API routers -- they never call the Kalshi API directly.

All routes here are behind require_login (see app/auth.py); the JSON API
under /api/* is left open.
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.auth import require_login
from app.db import get_db
from app.models import EtlRun, Event, Market

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _dashboard_context(db: Session) -> dict:
    """Small operator dashboard: last ETL run + current warehouse volume by
    category, so it's obvious at a glance whether the pipeline is healthy and
    what's actually loaded.
    """
    last_run = db.query(EtlRun).order_by(EtlRun.started_at.desc()).first()
    last_run_started_at_display = (
        last_run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC") if last_run else None
    )

    total_events = db.query(func.count(Event.event_ticker)).scalar() or 0
    total_markets = db.query(func.count(Market.ticker)).scalar() or 0

    category_counts = (
        db.query(
            func.coalesce(Event.category, "Uncategorized").label("category"),
            func.count(Market.ticker).label("market_count"),
        )
        .join(Market, Market.event_ticker == Event.event_ticker)
        .group_by("category")
        .order_by(func.count(Market.ticker).desc())
        .all()
    )

    return {
        "last_run": last_run,
        "last_run_started_at_display": last_run_started_at_display,
        "total_events": total_events,
        "total_markets": total_markets,
        "category_counts": category_counts,
    }


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": request.session.get("username"), **_dashboard_context(db)},
    )


@router.get("/ui/events")
def ui_events(request: Request, category: Optional[str] = None, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    query = db.query(Event)
    if category:
        query = query.filter(Event.category == category)
    events = query.order_by(Event.event_ticker).limit(200).all()

    categories = [row[0] for row in db.query(distinct(Event.category)).all() if row[0]]

    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "events": events,
            "categories": sorted(categories),
            "selected_category": category,
        },
    )


@router.get("/ui/events/{event_ticker}")
def ui_event_details(request: Request, event_ticker: str, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    event = db.query(Event).filter(Event.event_ticker == event_ticker).first()
    markets = (
        db.query(Market)
        .filter(Market.event_ticker == event_ticker)
        .order_by(Market.ticker)
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="event_details.html",
        context={"event": event, "event_ticker": event_ticker, "markets": markets},
    )
