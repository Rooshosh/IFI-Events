"""Handler for BrightData Facebook Group Scraper webhook results.

This endpoint receives Facebook group posts from BrightData's API
and processes them into events.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Body, BackgroundTasks
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
import os
import hmac
import hashlib
import json
from zoneinfo import ZoneInfo
import asyncio

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

async def process_webhook_data(data: dict, db: Session):
    """Process webhook data asynchronously."""
    try:
        # Check for "no posts" warning
        if isinstance(data, list) and len(data) == 1:
            first_item = data[0]
            if isinstance(first_item, dict) and first_item.get('warning_code') == 'dead_page':
                logger.info(f"No new posts found for the specified period: {first_item.get('warning')}")
                return
        
        # Convert list to dict if needed
        if isinstance(data, list):
            data = {"posts": data}
        
        # Process the data using the Facebook processor
        events = process_facebook_data(data)
        
        # Store processed events using NewEventHandler
        handler = NewEventHandler()  # Skip merging for now
        new_count, updated_count = handler.process_new_events(events, "Facebook (IFI-studenter)")
        
        logger.info(f"Processed {len(events)} events: {new_count} new, {updated_count} updated")
        
    except Exception as e:
        logger.error(f"Error processing webhook data: {e}")
        raise

@router.post("/brightdata/facebook-group/results")
async def handle_brightdata_facebook_group_webhook(
    background_tasks: BackgroundTasks,
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
        # Log incoming data for debugging (only if DEBUG level is enabled)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Received webhook data:")
            logger.debug(f"Data type: {type(data)}")
            logger.debug(f"Data keys (if dict): {data.keys() if isinstance(data, dict) else 'N/A'}")
            logger.debug(f"Data length (if list): {len(data) if isinstance(data, list) else 'N/A'}")
            if isinstance(data, list):
                logger.debug(json.dumps(data[0], indent=2) if data else "Empty list")
            else:
                logger.debug(json.dumps(next(iter(data.values())), indent=2) if data else "Empty dict")
        
        # Add processing task to background tasks
        background_tasks.add_task(process_webhook_data, data, db)
        
        # Return immediately
        return {
            "status": "success",
            "message": "Data received and queued for processing"
        }
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 