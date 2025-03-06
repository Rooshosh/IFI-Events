"""Webhook handlers for external services."""

from fastapi import APIRouter, HTTPException, Header, Depends, Body
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os
import hmac
import hashlib
import logging

from ..db.session import get_db
from ..models.event import Event
from ..models.raw_scrape_data import RawScrapeData
from ..utils.timezone import ensure_oslo_timezone

# Set up logging
logger = logging.getLogger(__name__)

# Create router for webhook endpoints
router = APIRouter(
    prefix="/webhook",
    tags=["webhooks"]
)

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

async def process_facebook_event(event_data: dict) -> Optional[Event]:
    """Process a Facebook event from BrightData and convert it to our Event model."""
    try:
        # Extract relevant fields from Facebook event data
        # Note: Adjust these field mappings based on actual BrightData response format
        title = event_data.get('name', '')
        description = event_data.get('description', '')
        start_time = event_data.get('start_time')
        end_time = event_data.get('end_time')
        location = event_data.get('place', {}).get('name') if event_data.get('place') else None
        source_url = event_data.get('permalink_url')
        
        # Convert timestamps to datetime objects
        if start_time:
            start_time = ensure_oslo_timezone(datetime.fromisoformat(start_time.replace('Z', '+00:00')))
        if end_time:
            end_time = ensure_oslo_timezone(datetime.fromisoformat(end_time.replace('Z', '+00:00')))
        
        # Create Event object
        event = Event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            source_url=source_url,
            source_name='facebook',
            fetched_at=datetime.now()
        )
        
        return event
    except Exception as e:
        logger.error(f"Error processing Facebook event: {e}")
        return None

@router.post("/brightdata/results")
async def brightdata_results_webhook(
    data: dict | list = Body(..., media_type="application/json"),
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for receiving BrightData scraping results.
    Currently only logging the data for debugging.
    """
    # Log incoming data for debugging
    logger.info(f"Received webhook data: {data}")
    logger.info(f"Authorization header: {authorization}")
    
    # Convert list to dict if needed
    if isinstance(data, list):
        data = {"events": data}
    
    # Verify BrightData authorization
    if authorization != os.environ.get('BRIGHTDATA_AUTHORIZATION_HEADER'):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
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
    
    return {
        "status": "success",
        "message": "Data received and stored",
        "data": data
    } 