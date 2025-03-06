"""API routes initialization."""

from fastapi import APIRouter
from .events import router as events_router
from .health import router as health_router
from .webhook import router as webhook_router

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(events_router, prefix="/events", tags=["events"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(webhook_router, prefix="/webhook", tags=["webhook"]) 