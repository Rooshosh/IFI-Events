"""Handler for BrightData webhook results."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
import os
import hmac
import hashlib

from src.db.session import get_db
from src.models.event import Event
from src.models.raw_scrape_data import RawScrapeData
from src.processors.facebook import FacebookProcessor
from src.utils.timezone import ensure_oslo_timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])

# Security
BRIGHTDATA_AUTH_HEADER = APIKeyHeader(name="Authorization")

def verify_brightdata_signature(signature: str, payload: dict) -> bool:
    """Verify the BrightData webhook signature."""
    if not os.environ.get('BRIGHTDATA_AUTHORIZATION_HEADER'):
        logger.warning("BRIGHTDATA_AUTHORIZATION_HEADER not set, skipping signature verification")
        return True
    
    # Get the raw payload as string
    payload_str = str(payload)
    
    # Calculate expected signature
    expected_signature = hmac.new(
        os.environ['BRIGHTDATA_AUTHORIZATION_HEADER'].encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

async def verify_brightdata_auth(auth_header: str = Depends(BRIGHTDATA_AUTH_HEADER)):
    """Verify the BrightData webhook authorization header"""
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if auth_header != os.environ.get('BRIGHTDATA_AUTHORIZATION_HEADER'):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    return auth_header

@router.post("/brightdata/results")
async def handle_brightdata_webhook(
    data: dict | list = Body(..., media_type="application/json"),
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
    """
    Handle webhook results from BrightData.
    
    This endpoint receives Facebook group posts from BrightData's API
    and processes them into events.
    """
    try:
        # Log incoming data for debugging
        logger.info(f"Received webhook data: {data}")
        logger.info(f"Authorization header: {authorization}")
        
        # Convert list to dict if needed
        if isinstance(data, list):
            data = {"events": data}
        
        # Store the raw data in the database
        try:
            raw_data = RawScrapeData(
                source='brightdata_facebook',
                raw_data=data,
                created_at=datetime.now()
            )
            db.add(raw_data)
            db.commit()
            logger.info(f"Successfully stored raw data with ID: {raw_data.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing raw data: {e}")
            # Continue processing even if storage fails
        
        # Log the structure of the data
        logger.info("Data structure:")
        if "events" in data:
            for i, event in enumerate(data["events"]):
                logger.info(f"Event {i + 1}:")
                for key, value in event.items():
                    logger.info(f"  {key}: {value}")
        
        # Initialize the Facebook processor
        processor = FacebookProcessor()
        
        # Process the data
        events = processor.process_data(data)
        
        # TODO: Store processed events in database
        # This should be handled by the NewEventHandler
        
        return {
            "status": "success",
            "message": "Data received, stored, and processed",
            "events_processed": len(events),
            "raw_data_id": raw_data.id if 'raw_data' in locals() else None
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 