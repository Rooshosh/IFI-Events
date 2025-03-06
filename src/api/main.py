"""Main FastAPI application module."""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
from dotenv import load_dotenv
import subprocess
from pathlib import Path

load_dotenv()

from ..db.session import db_manager, init_db
from ..models.event import Event
from src.webhooks.routes import router as webhook_router
from src.utils.logging_config import setup_logging

# Set up logging
setup_logging()

# Get environment setting
environment = os.environ.get('ENVIRONMENT', 'development')

app = FastAPI(
    title="IFI Events API",
    description="API for managing and processing events from various sources",
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

# Include routers
app.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])

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
    """Root endpoint."""
    return {"message": "Welcome to the IFI Events API"}

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

# Fetch trigger endpoint
@app.post("/admin/fetch")
async def trigger_fetch(authorization: str = Header(...)):
    """Trigger a fetch of new events from all sources."""
    expected_token = os.environ.get('ADMIN_API_KEY')
    if not expected_token:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Invalid authorization token")
    
    try:
        # Get the path to the script
        script_path = Path(__file__).parent.parent.parent / 'scripts' / 'get_new_data.py'
        
        # Run the script
        result = subprocess.run(['python', str(script_path)], 
                              capture_output=True, 
                              text=True)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Script failed: {result.stderr}"
            )
        
        return {
            "status": "success",
            "message": "Fetch completed successfully",
            "details": result.stdout
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run fetch script: {str(e)}"
        ) 