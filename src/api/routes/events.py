"""Events routes for the FastAPI application."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from ...db import db
from ...models.event import Event

router = APIRouter(tags=["events"])

@router.get("/events")
async def get_events() -> List[Dict[str, Any]]:
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

@router.get("/events/{event_id}")
async def get_event(event_id: int) -> Dict[str, Any]:
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