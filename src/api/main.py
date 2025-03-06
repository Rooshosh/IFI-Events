from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import logging

from ..db.session import db_manager, init_db
from ..models.event import Event
from ..webhooks import router as webhook_router

# Set up logging
logger = logging.getLogger(__name__)

# Get environment setting
environment = os.environ.get('ENVIRONMENT', 'development')

app = FastAPI(
    title="IFI Events API",
    description="API for IFI Events",
    version="1.0.0",
    docs_url=None if environment == 'production' else '/docs',  # Disable docs in production
    redoc_url=None if environment == 'production' else '/redoc'  # Disable redoc in production
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Enable CORS with environment-specific settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if environment == 'development' else [],  # Restrict CORS in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook routers
app.include_router(webhook_router)

# Dependency to get DB session
def get_db():
    """Get a database session."""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db_manager.close_session()

# Test endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to IFI Events API"}

# Events endpoint
@app.get("/events")
async def get_events(db: Session = Depends(get_db)):
    """Get all future and ongoing events."""
    now = datetime.now()
    events = db.query(Event).filter(
        (Event.start_time > now) |  # Future events
        ((Event.start_time <= now) & (Event.end_time >= now))  # Ongoing events
    ).order_by(Event.start_time).all()
    return [event.to_dict() for event in events]

# Single event endpoint
@app.get("/events/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get a single event by ID."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict() 