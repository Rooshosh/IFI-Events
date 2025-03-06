"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...db.base import get_db
from sqlalchemy import text

router = APIRouter()

@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """Check the health of the API and database."""
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        } 