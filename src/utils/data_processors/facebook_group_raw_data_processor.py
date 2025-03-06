"""Processor for Facebook group raw data.

This module processes raw Facebook group data to identify and parse events.
It uses LLM to determine if a post is an event and extract relevant information.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from zoneinfo import ZoneInfo

from src.models.event import Event
from src.utils.llm import analyze_facebook_post
from src.utils.data_processors.store_raw_data import RawDataHandler

logger = logging.getLogger(__name__)

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
            fetched_at=datetime.now(ZoneInfo("Europe/Oslo"))
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
    
    This function:
    1. Analyzes each post using LLM to determine if it's an event
    2. Parses posts identified as events into Event objects
    3. Stores raw data with processing status
    
    Args:
        data: The webhook payload from BrightData
        
    Returns:
        List[Event]: List of parsed events
    """
    try:
        # Extract posts from the data
        posts = data.get('posts', [])
        if not posts:
            logger.warning("No posts found in data")
            return []
        
        logger.info(f"Processing {len(posts)} posts from Facebook")
        
        # Initialize raw data handler
        raw_data_handler = RawDataHandler()
        
        # Process each post
        events: List[Event] = []
        raw_data_entries = []
        
        for post in posts:
            try:
                # Analyze post using LLM
                is_event, analysis = analyze_facebook_post(post)
                
                # Prepare raw data entry
                raw_data_entry = {
                    'raw_data': post,
                    'processing_status': {
                        'is_event': is_event,
                        'analysis': analysis,
                        'processed_at': datetime.now().isoformat()
                    }
                }
                raw_data_entries.append(raw_data_entry)
                
                # If it's an event, create Event object
                if is_event:
                    event = _create_event_from_post(post)
                    events.append(event)
                    logger.info(f"Created event: {event.title} ({event.start_time})")
                else:
                    logger.debug(f"Post not identified as event: {post.get('title', 'No title')}")
                    
            except Exception as e:
                logger.error(f"Failed to process post: {e}")
                continue
        
        # Store raw data entries
        if raw_data_entries:
            raw_data_handler.store_batch('brightdata_facebook_group', raw_data_entries)
        
        logger.info(f"Successfully processed {len(events)} events from {len(posts)} posts")
        return events
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return []
