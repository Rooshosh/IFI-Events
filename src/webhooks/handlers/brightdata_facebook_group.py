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
from src.models.raw_scrape_data import RawScrapeData
from src.utils.timezone import now_oslo

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

def _parse_post_date(date_str: str) -> datetime:
    """Parse a post's date string into a datetime object"""
    try:
        # Example format: "2024-03-19T14:30:00"
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.astimezone(ZoneInfo("Europe/Oslo"))
    except Exception as e:
        logger.error(f"Error parsing date {date_str}: {e}")
        raise

def _create_event_from_post(post: Dict[str, Any]) -> Event:
    """Convert a Facebook post into an Event object"""
    try:
        # Extract post data
        title = post.get('title', 'Facebook Post')
        description = post.get('description', '')
        post_date = _parse_post_date(post.get('date', ''))
        post_url = post.get('url', '')
        
        # Create event
        event = Event(
            title=title,
            description=description,
            start_time=post_date,
            end_time=None,  # Facebook posts don't have end times
            location=None,  # Facebook posts don't have locations
            source_url=post_url,
            source_name="Facebook (IFI-studenter)",
            fetched_at=now_oslo()
        )
        
        # Add author if available
        if post.get('author'):
            event.author = post['author']
        
        return event
        
    except Exception as e:
        logger.error(f"Error creating event from post: {e}")
        raise

def process_facebook_data(data: Dict[str, Any]) -> List[Event]:
    """
    Process BrightData webhook data containing Facebook posts.
    
    Args:
        data: The webhook payload from BrightData
        
    Returns:
        List[Event]: List of events created from the posts
    """
    try:
        # Log the incoming data for debugging
        logger.debug(f"Received data: {json.dumps(data, indent=2)}")
        
        # Extract posts from the data
        posts = data.get('posts', [])
        if not posts:
            logger.warning("No posts found in data")
            return []
        
        logger.info(f"Processing {len(posts)} posts from Facebook")
        
        # Process each post
        events: List[Event] = []
        for post in posts:
            try:
                event = _create_event_from_post(post)
                events.append(event)
                logger.info(f"Created event: {event.title} ({event.start_time})")
            except Exception as e:
                logger.error(f"Failed to process post: {e}")
                continue
        
        logger.info(f"Successfully processed {len(events)} events from {len(posts)} posts")
        return events
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return []

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
        
        # Store the raw data in the database
        try:
            raw_data = RawScrapeData(
                source='brightdata_facebook_group',
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
        
        # Process the data
        events = process_facebook_data(data)
        
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