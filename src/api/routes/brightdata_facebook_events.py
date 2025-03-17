"""Routes for receiving Facebook Event data via BrightData's API."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Header, Body, BackgroundTasks

from ...models.event import Event
from ...new_event_handler import process_new_events
from ...utils.data_processors.parse_facebook_events import process_facebook_event_data
from ...config.external_services import verify_brightdata_auth

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/brightdata",
    tags=["brightdata"]
)

async def process_facebook_events(data: dict):
    """Process received Facebook Event data asynchronously."""
    try:
        # Check for "no events" warning
        if isinstance(data, list) and len(data) == 1:
            first_item = data[0]
            if isinstance(first_item, dict) and first_item.get('warning_code') == 'dead_page':
                logger.info(f"No events found: {first_item.get('warning')}")
                return
        
        # Convert list to dict if needed
        if isinstance(data, list):
            data = {"events": data}
        
        # Process the data using the Facebook Event processor
        events = process_facebook_event_data(data)
        
        # Store any events found
        new_count, updated_count = process_new_events(events, "Facebook Events")
        
        logger.info(f"Processed {len(events)} events: {new_count} new, {updated_count} updated")
        
    except Exception as e:
        logger.error(f"Error processing Facebook Events: {e}")
        raise

@router.post("/facebook-events/results")
async def receive_facebook_events(
    background_tasks: BackgroundTasks,
    data: dict | list = Body(..., media_type="application/json"),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Receive and process Facebook Event data via BrightData.
    
    This endpoint receives Facebook Event data from BrightData's API
    and processes it to extract event information.
    """
    try:
        # Verify authorization
        if not verify_brightdata_auth(authorization):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header"
            )
        
        # Log incoming data for debugging (only if DEBUG level is enabled)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Received Facebook Event data:")
            logger.debug(f"Data type: {type(data)}")
            logger.debug(f"Data keys (if dict): {data.keys() if isinstance(data, dict) else 'N/A'}")
            logger.debug(f"Data length (if list): {len(data) if isinstance(data, list) else 'N/A'}")
        
        # Add processing task to background tasks
        background_tasks.add_task(process_facebook_events, data)
        
        # Return immediately
        return {
            "status": "success",
            "message": "Facebook Event data received and queued for processing"
        }
        
    except Exception as e:
        logger.error(f"Error handling Facebook Event data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 