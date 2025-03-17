"""FastAPI application configuration module."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal imports
from src.config.environment import IS_PRODUCTION_ENVIRONMENT # ¿ Environment must be imported first ?
from src.config.cors import CORS_CONFIG
from src.utils.logging_config import setup_logging
from src.db import db
from .routes import (
    brightdata_facebook_posts,
    brightdata_facebook_events,
    event_queries,
    event_fetch_trigger,
    health
)

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    try:
        db.ensure_tables_exist()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    yield
    # Shutdown
    # Add cleanup here if needed

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="IFI Events API",
        description="API for managing and processing events from various sources",
        version="1.0.0",
        docs_url=None if IS_PRODUCTION_ENVIRONMENT else '/api/docs',
        redoc_url=None if IS_PRODUCTION_ENVIRONMENT else '/api/redoc',
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)

    # Include health check router without prefix
    app.include_router(health.router)

    # Include routers with prefix
    app.include_router(event_queries.router, prefix="/api")
    app.include_router(event_fetch_trigger.router, prefix="/api")
    app.include_router(brightdata_facebook_posts.router, prefix="/webhook")
    app.include_router(brightdata_facebook_events.router, prefix="/webhook")

    return app

# Create the application instance
app = create_application() 