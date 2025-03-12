"""Main FastAPI application module."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal imports - environment must be first
from src.config.environment import IS_PRODUCTION_ENVIRONMENT
from src.config.cors import CORS_CONFIG
from src.utils.logging_config import setup_logging
from ..db import db
from .routes import events, admin, brightdata

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
        logger.error(f"Database initialization failed: {e}")
    yield
    # Shutdown
    # Add cleanup here if needed

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="IFI Events API",
        description="API for managing and processing events from various sources",
        version="1.0.0",
        docs_url=None if IS_PRODUCTION_ENVIRONMENT else '/docs',
        redoc_url=None if IS_PRODUCTION_ENVIRONMENT else '/redoc',
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)

    # Include routers
    app.include_router(events.router)
    app.include_router(admin.router)
    app.include_router(brightdata.router)

    @app.get("/", tags=["health"])
    async def root():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": "production" if IS_PRODUCTION_ENVIRONMENT else "development",
            "version": app.version
        }

    return app

# Create the application instance
app = create_application() 