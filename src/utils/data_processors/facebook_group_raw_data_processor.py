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
import re

from src.models.event import Event
from src.utils.llm import is_event_post, parse_event_details
from src.utils.data_processors.db_store_raw_data import db_store_batch

# TODO: Prob use this system of a separate data processor script for the other scrapers as well

logger = logging.getLogger(__name__)

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

def _has_facebook_event(post: Dict[str, Any]) -> bool:
    """
    Check if a post contains a Facebook Event link.
    
    A post can contain an Event link in two ways:
    1. As an attachment of type 'ProfilePicAttachmentMedia' with an Event URL
    2. As a direct link in the post content
    
    Args:
        post: Raw post data from Facebook
        
    Returns:
        bool: True if the post contains a Facebook Event link
    """
    return len(_extract_facebook_event_links(post)) > 0

def _process_facebook_event_post(post: Dict[str, Any]) -> Optional[Event]:
    """
    Process a post that contains a Facebook Event attachment.
    
    This method will:
    1. Extract the Event ID from the attachment URL
    2. Fetch the Event details using BrightData's API
    3. Create an Event object from the Event details
    
    Args:
        post: Raw post data from Facebook
        
    Returns:
        Optional[Event]: Event object if successful, None otherwise
        
    Raises:
        NotImplementedError: Currently not implemented
    """
    event_links = _extract_facebook_event_links(post)
    if event_links:
        logger.info(f"Found Facebook Event links: {event_links}")
    raise NotImplementedError("Facebook Event processing not implemented yet")

def _extract_facebook_event_links(post: Dict[str, Any]) -> List[str]:
    """
    Extract all Facebook Event links from a post.
    
    A post can contain Event links in two ways:
    1. As attachments of type 'ProfilePicAttachmentMedia' with Event URLs
    2. As direct links in the post content
    
    Args:
        post: Raw post data from Facebook
        
    Returns:
        List[str]: List of Facebook Event URLs found in the post
    """
    event_links = []
    
    # Check attachments for Event links
    attachments = post.get('attachments', [])
    for attachment in attachments:
        # Check for Event attachment
        if attachment.get('type') == 'ProfilePicAttachmentMedia':
            attachment_url = attachment.get('attachment_url', '')
            if attachment_url.startswith('https://www.facebook.com/events/'):
                event_links.append(attachment_url)
    
    # Check post content for Event links
    content = post.get('content', '')
    # Look for URLs that match the Facebook Event pattern
    event_urls = re.findall(r'https://www\.facebook\.com/events/\d+/', content)
    event_links.extend(event_urls)
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(event_links))

def process_facebook_group_data(data: Dict[str, Any]) -> List[Event]:
    """
    Process raw Facebook group data to extract events.
    
    A post is considered an event if:
    1. It contains a Facebook Event attachment, OR
    2. The LLM determines it to be an event based on its content
    
    Args:
        data: Raw data from Facebook group scrape
        
    Returns:
        List[Event]: List of extracted events
    """
    try:
        posts = data.get('posts', [])
        if not posts:
            logger.warning("No posts found in data")
            return []
        
        total_posts = len(posts)
        logger.info(f"Processing {total_posts} posts from Facebook")
        
        events: List[Event] = []
        raw_data_entries = []
        
        for post in posts:
            try:
                # Skip posts without content
                if not post.get('content'):
                    continue
                
                # Try to create event from Facebook Event link first
                event = None
                if _has_facebook_event(post):
                    try:
                        event = _process_facebook_event_post(post)
                    except NotImplementedError:
                        logger.warning("Facebook Event processing not implemented yet")
                
                # If no Facebook Event, try LLM processing
                if not event:
                    content = f"{post.get('post_external_title', '')}\n\n{post.get('content', '')}"
                    is_event, _ = is_event_post(
                        content=content,
                        post_date=post.get('date_posted'),
                        author=post.get('user_username_raw')
                    )
                    
                    if is_event:
                        event_details = parse_event_details(
                            content=content,
                            url=post.get('url', ''),
                            post_date=post.get('date_posted'),
                            author=post.get('user_username_raw')
                        )
                        if event_details:
                            try:
                                event = _create_event_from_post(post, event_details)
                            except ValueError as e:
                                logger.warning(f"Could not create event: {e}")
                
                # If we successfully created an event, add it to the list
                if event:
                    events.append(event)
                
                # Store raw data with processing status
                raw_data_entry = {
                    'raw_data': post,
                    'processing_status': 'success' if event else 'not_an_event',
                    'created_at': _parse_post_date(post.get('date_posted'))
                }
                raw_data_entries.append(raw_data_entry)
                    
            except Exception as e:
                logger.error(f"Failed to process post: {e}")
                continue
        
        # Store raw data entries
        if raw_data_entries:
            try:
                db_store_batch('brightdata_facebook_group', raw_data_entries)
            except Exception as e:
                logger.error(f"Failed to store raw data: {e}")
        
        logger.info(f"Successfully processed {len(events)} events from {len(posts)} posts")
        return events
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return []
