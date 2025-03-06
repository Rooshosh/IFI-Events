"""Handler for BrightData Facebook Group Scraper webhook results.

This endpoint receives Facebook group posts from BrightData's API
and processes them into events.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
import os
import hmac
import hashlib
import json
from zoneinfo import ZoneInfo

from src.db.session import get_db
from src.models.event import Event
from src.new_event_handler import NewEventHandler
from src.utils.data_processors.facebook_group_raw_data_processor import process_facebook_data

logger = logging.getLogger(__name__)

# Create router without prefix (it's handled by the main webhook router)
router = APIRouter(tags=["brightdata_facebook_group"])

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

@router.post("/brightdata/facebook-group/results")
async def handle_brightdata_facebook_group_webhook(
    data: dict | list = Body(..., media_type="application/json"),
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
    """
    Handle webhook results from BrightData's Facebook Group Scraper.
    
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
        
        # Process the data using the Facebook processor
        events = process_facebook_data(data)
        
        # Store processed events using NewEventHandler
        handler = NewEventHandler()  # Skip merging for now
        new_count, updated_count = handler.process_new_events(events, "Facebook (IFI-studenter)")
        
        return {
            "status": "success",
            "message": "Data received and processed",
            "events_processed": len(events),
            "new_events": new_count,
            "updated_events": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 