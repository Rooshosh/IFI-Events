"""Health check routes for the FastAPI application."""

from fastapi import APIRouter
from src.config.environment import IS_PRODUCTION_ENVIRONMENT

router = APIRouter(tags=["health"])

@router.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": "production" if IS_PRODUCTION_ENVIRONMENT else "development",
        "version": "1.0.0"  # This should ideally come from a central version config
    } 