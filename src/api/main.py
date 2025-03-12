"""Main FastAPI application module."""

import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Internal imports
from ..db import db
from .webhooks.routes import router as webhook_router
from .routes.events import router as events_router
from .routes.admin import router as admin_router
from src.utils.logging_config import setup_logging

# Constants and configurations
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

ALLOWED_ORIGINS = {
    'development': ["*"],  # Allow all in development
    'production': [
        "https://ifi.events",          # Main frontend
        "https://www.ifi.events",      # With www
        "https://api.ifi.events",      # API domain
    ]
}

ALLOWED_METHODS = [
    "GET",      # For fetching events
    "POST",     # For webhooks and admin endpoints
    "OPTIONS"   # Required for CORS preflight
]

ALLOWED_HEADERS = [
    "Authorization",  # For admin endpoints
    "Content-Type",   # For request bodies
    "Accept",        # For content negotiation
]

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="IFI Events API",
        description="API for managing and processing events from various sources",
        version="1.0.0",
        docs_url=None if ENVIRONMENT == 'production' else '/docs',
        redoc_url=None if ENVIRONMENT == 'production' else '/redoc'
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS[ENVIRONMENT],
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        expose_headers=[],
        max_age=3600,
    )

    # Include routers
    app.include_router(events_router, tags=["events"])
    app.include_router(admin_router, tags=["admin"])
    app.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])

    @app.get("/", tags=["health"])
    async def root():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": ENVIRONMENT,
            "version": app.version
        }

    return app

# Create the application instance
app = create_application()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and ensure tables exist."""
    try:
        db.ensure_tables_exist()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise - let the app start and retry on first request

# Events endpoint
@app.get("/events")
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

# Single event endpoint
@app.get("/events/{event_id}")
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
        
        if result.returncode != 0:
            raise Exception(f"Script failed with error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Script timed out after 5 minutes")
    except Exception as e:
        raise Exception(f"Failed to run fetch script: {str(e)}")

@app.post("/admin/fetch")
async def trigger_fetch(
    background_tasks: BackgroundTasks,
    authorization: str = Header(...)
):
    """
    Trigger a fetch of new events.
    This endpoint is protected by an authorization header.
    """
    # Check authorization
    if authorization != os.environ.get('ADMIN_API_KEY'):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization"
        )
    
    # Add fetch task to background tasks
    background_tasks.add_task(run_fetch_script)
    
    return {
        "status": "success",
        "message": "Fetch task started"
    } 