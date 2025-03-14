"""FastAPI application configuration module."""

# Environment must be imported first
from src.config.environment import IS_PRODUCTION_ENVIRONMENT

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal imports
from src.config.cors import CORS_CONFIG
from src.utils.logging_config import setup_logging
from src.db import db
from src.config.external_services.openai import init_openai_client
from .routes import event_queries, event_fetch_trigger, brightdata_facebook_ifi_receiver

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
        
        # Initialize OpenAI client
        init_openai_client()
        logger.info("OpenAI client initialized successfully")
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
        docs_url=None if IS_PRODUCTION_ENVIRONMENT else '/docs',
        redoc_url=None if IS_PRODUCTION_ENVIRONMENT else '/redoc',
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)

    # Include routers
    app.include_router(event_queries.router)
    app.include_router(event_fetch_trigger.router)
    app.include_router(brightdata_facebook_ifi_receiver.router)

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