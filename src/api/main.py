"""Main FastAPI application module."""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
from dotenv import load_dotenv
import subprocess
from pathlib import Path

load_dotenv()

from ..db.database_manager import db_manager, init_db
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
    """Initialize database only once during startup."""
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization failed: {str(e)}")
        # Don't raise the exception - allow the app to start even if DB init fails
        # The first request will retry the initialization

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

async def run_fetch_script():
    """Background task to run the fetch script."""
    try:
        script_path = Path(__file__).parent.parent.parent / 'scripts' / 'get_new_data.py'
        # Run the script with a timeout to prevent hanging
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Log the output for debugging
        if result.stdout:
            print(f"Script output: {result.stdout}")
        if result.stderr:
            print(f"Script errors: {result.stderr}")
            
        if result.returncode != 0:
            print(f"Script failed with return code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("Script timed out after 5 minutes")
    except Exception as e:
        print(f"Background fetch failed: {str(e)}")

# Fetch trigger endpoint
@app.post("/admin/fetch")
async def trigger_fetch(
    background_tasks: BackgroundTasks,
    authorization: str = Header(...)
):
    """Trigger a fetch of new events from all sources."""
    expected_token = os.environ.get('ADMIN_API_KEY')
    if not expected_token:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Invalid authorization token")
    
    # Add the fetch task to background tasks
    background_tasks.add_task(run_fetch_script)
    
    return {
        "status": "success",
        "message": "Fetch request received and processing started in background"
    } 