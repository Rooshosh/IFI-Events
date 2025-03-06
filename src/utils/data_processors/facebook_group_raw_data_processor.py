"""Processor for Facebook group raw data.

This module processes raw Facebook group data to identify and parse events.
It uses LLM to determine if a post is an event and extract relevant information.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json

from src.models.event import Event
from src.utils.llm import is_event_post, parse_event_details, init_openai
from src.utils.data_processors.store_raw_data import RawDataHandler

logger = logging.getLogger(__name__)

# Initialize LLM client
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    logger.error("OPENAI_API_KEY environment variable not set")
else:
    init_openai(api_key)

# LLM configuration
LLM_CONFIG = {
    'model': 'gpt-4-turbo-preview',
    'temperature': 0.3,
    'max_tokens': 500
}

def _parse_post_date(date_str: str) -> Optional[datetime]:
    """
    Parse a post's date string into a datetime object.
    
    Handles multiple date formats and returns None if parsing fails.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
        
    try:
        # Try ISO format (2024-03-19T14:30:00)
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.astimezone(ZoneInfo("Europe/Oslo"))
    except ValueError:
        # Log the error but don't raise an exception
        logger.warning(f"Could not parse date string: {date_str}")
        return None

def _create_event_from_post(post: Dict[str, Any], event_details: Dict[str, Any]) -> Event:
    """
    Convert a Facebook post into an Event object using LLM-parsed details.
    
    Args:
        post: Raw post data from Facebook
        event_details: Structured event details parsed by LLM
        
    Returns:
        Event object
        
    Raises:
        ValueError: If required event data is missing
    """
    try:
        # Get title (required field)
        title = event_details.get('title') or post.get('post_external_title')
        if not title:
            raise ValueError("Cannot create event without a title")
            
        # Get description (optional)
        description = event_details.get('description') or post.get('content', '')
        
        # Get start time (required field)
        start_time = None
        if event_details.get('start_time'):
            start_time = _parse_post_date(event_details['start_time'])
        if not start_time and post.get('date_posted'):
            start_time = _parse_post_date(post['date_posted'])
        if not start_time:
            # If no start time can be parsed, use current time as fallback
            logger.warning(f"No valid start time found for event: {title}, using current time")
            start_time = datetime.now(ZoneInfo("Europe/Oslo"))
        
        # Get end time (optional)
        end_time = None
        if event_details.get('end_time'):
            end_time = _parse_post_date(event_details['end_time'])
            
        # Get location (optional)
        location = event_details.get('location')
        
        # Get URL (optional)
        post_url = post.get('url', '')
        
        # Create event
        event = Event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            source_url=post_url,
            source_name="Facebook (IFI-studenter)",
            fetched_at=datetime.now(ZoneInfo("Europe/Oslo"))
        )
        
        # Add author if available
        if post.get('user_username_raw'):
            event.author = post['user_username_raw']
        
        return event
        
    except Exception as e:
        logger.error(f"Error creating event from post: {e}")
        raise

def process_facebook_data(data: Dict[str, Any]) -> List[Event]:
    """
    Process BrightData webhook data containing Facebook posts.
    
    This function:
    1. Analyzes each post using LLM to determine if it's an event
    2. For posts identified as events, extracts detailed event information
    3. Creates Event objects from the parsed information
    4. Stores raw data with processing status
    
    Expected data format from BrightData:
    {
        "posts": [
            {
                "content": "Post content",
                "date_posted": "2024-03-19T14:30:00",
                "url": "https://facebook.com/...",
                "user_username_raw": "Post author",
                "post_external_title": "Optional external title",
                ...
            },
            ...
        ]
    }
    
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
                # Skip posts without content
                if not post.get('content'):
                    logger.warning("Skipping post without content")
                    continue
                
                # Prepare post content for LLM analysis
                content = f"{post.get('post_external_title', '')}\n\n{post.get('content', '')}"
                url = post.get('url', '')
                
                # First, determine if this is an event
                is_event, event_explanation = is_event_post(content, LLM_CONFIG)
                
                # Prepare raw data entry with initial analysis
                processing_status = {
                    'is_event': is_event,
                    'event_explanation': event_explanation,
                    'processed_at': datetime.now().isoformat()
                }
                
                # If it's an event, extract detailed information
                if is_event:
                    event_details = parse_event_details(content, url, LLM_CONFIG)
                    if event_details:
                        # Add event details to processing status
                        processing_status['event_details'] = event_details
                        
                        try:
                            # Create event object
                            event = _create_event_from_post(post, event_details)
                            events.append(event)
                            logger.info(f"Created event: {event.title} ({event.start_time})")
                        except ValueError as e:
                            logger.warning(f"Could not create event: {e}")
                    else:
                        logger.warning(f"Failed to parse event details for post: {post.get('post_external_title', 'No title')}")
                else:
                    logger.debug(f"Post not identified as event: {post.get('post_external_title', 'No title')}")
                
                raw_data_entry = {
                    'raw_data': post,
                    'processing_status': json.dumps(processing_status)
                }
                raw_data_entries.append(raw_data_entry)
                    
            except Exception as e:
                logger.error(f"Failed to process post: {e}")
                continue
        
        # Store raw data entries
        if raw_data_entries:
            try:
                raw_data_handler.store_batch('brightdata_facebook_group', raw_data_entries)
            except Exception as e:
                logger.error(f"Failed to store raw data: {e}")
                # Continue processing even if storage fails
        
        logger.info(f"Successfully processed {len(events)} events from {len(posts)} posts")
        return events
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return []
