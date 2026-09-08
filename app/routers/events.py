from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.schemas import EventOut

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=List[EventOut])
def list_events(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Event]:
    query = db.query(Event)
    if category:
        query = query.filter(Event.category == category)
    if status:
        query = query.filter(Event.status == status)
    return query.order_by(Event.event_ticker).offset(offset).limit(limit).all()


@router.get("/{event_ticker}", response_model=EventOut)
def get_event(event_ticker: str, db: Session = Depends(get_db)) -> Event:
    event = db.query(Event).filter(Event.event_ticker == event_ticker).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
