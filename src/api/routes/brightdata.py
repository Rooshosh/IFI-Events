"""BrightData webhook routes for the FastAPI application."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Header, Body, BackgroundTasks

from ...models.event import Event
from ...new_event_handler import process_new_events
from ...utils.data_processors.facebook_group_raw_data_processor import process_facebook_data
from ...config.external_services import verify_brightdata_auth

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhook/brightdata",
    tags=["brightdata"]
)

async def process_webhook_data(data: dict):
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
        
        # Store processed events
        new_count, updated_count = process_new_events(events, "Facebook (IFI-studenter)")
        
        logger.info(f"Processed {len(events)} events: {new_count} new, {updated_count} updated")
        
    except Exception as e:
        logger.error(f"Error processing webhook data: {e}")
        raise

@router.post("/facebook-group/results")
async def handle_brightdata_facebook_group_webhook(
    background_tasks: BackgroundTasks,
    data: dict | list = Body(..., media_type="application/json"),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Handle webhook results from BrightData's Facebook Group Scraper.
    
    This endpoint receives Facebook group posts from BrightData's API
    and processes them into events.
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
            logger.debug("Received webhook data:")
            logger.debug(f"Data type: {type(data)}")
            logger.debug(f"Data keys (if dict): {data.keys() if isinstance(data, dict) else 'N/A'}")
            logger.debug(f"Data length (if list): {len(data) if isinstance(data, list) else 'N/A'}")
        
        # Add processing task to background tasks
        background_tasks.add_task(process_webhook_data, data)
        
        # Return immediately
        return {
            "status": "success",
            "message": "Data received and queued for processing"
        }
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 