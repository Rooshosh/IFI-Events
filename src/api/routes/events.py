"""Events router module."""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List, Dict

from ...db import db
from ...models.event import Event

router = APIRouter(tags=["events"])

@router.get("/events", response_model=List[Dict])
async def get_events():
    """Get all future and ongoing events."""
    try:
        with db.session() as session:
            now = datetime.now()
            events = session.query(Event).filter(
                (Event.start_time > now) |  # Future events
                ((Event.start_time <= now) & (Event.end_time >= now))  # Ongoing events
            ).order_by(Event.start_time).all()
            return [event.to_dict() for event in events]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/events/{event_id}", response_model=Dict)
async def get_event(event_id: int):
    """Get a single event by ID."""
    try:
        with db.session() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            return event.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 