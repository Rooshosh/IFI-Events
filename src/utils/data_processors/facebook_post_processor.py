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
from src.models.raw_scrape_data import ScrapedPost
from src.utils.llm import is_event_post, parse_event_details
from src.scrapers.facebook_event import FacebookEventScraper
from src.db import db, DatabaseError, with_retry

# Configuration
# TODO: Disable and/or remove this flag
SKIP_LLM_INTERPRETATION = False  # If True, only process posts with Facebook Event links

logger = logging.getLogger(__name__)

@with_retry()
def _store_scraped_posts(posts: List[Dict[str, Any]]) -> List[int]:
    """
    Store scraped posts in the database.
    
    Args:
        posts: List of dictionaries containing:
            - post_url: URL of the scraped post
            - event_status: Status indicating if the post is about an event
                          ('contains-event', 'is-event-llm', 'not-event-llm')
            - scraped_at: When the post was scraped
            
    Returns:
        List[int]: List of IDs of stored entries
        
    Raises:
        DatabaseError: If there is an error storing the data
    """
    stored_ids = []
    
    try:
        with db.session() as session:
            for post in posts:
                post_entry = ScrapedPost(
                    post_url=post['post_url'],
                    event_status=post['event_status'],
                    scraped_at=post['scraped_at']
                )
                session.add(post_entry)
                session.flush()  # Get the ID without committing
                stored_ids.append(post_entry.id)
            
            # All entries will be committed in a single transaction
        
        logger.info(f"Successfully stored {len(stored_ids)} posts in batch")
        return stored_ids
        
    except Exception as e:
        logger.error(f"Failed to store batch: {str(e)}")
        raise DatabaseError(f"Failed to store batch: {str(e)}") from e

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

def process_facebook_post_scrape_data(data: Dict[str, Any]) -> List[Event]:
    """
    Process raw Facebook group data to extract events.
    
    A post is considered an event if:
    1. It contains a Facebook Event attachment, OR
    2. The LLM determines it to be an event based on its content
    
    The function will:
    1. Filter out posts that have already been processed
    2. Split remaining posts into two lists based on whether they contain Facebook Event links
    3. Store posts with event links in the database
    4. Trigger a scrape for posts with Event links using FacebookEventScraper
    5. Process non-Event posts with LLM if SKIP_LLM_INTERPRETATION is false
    6. Store posts processed by LLM with their determined event status
    7. Parse posts into Event objects
    
    Args:
        data: Raw data from Facebook group scrape
        
    Returns:
        List[Event]: List of extracted events
    """
    try:
        # Store the timestamp when processing starts
        processing_start_time = datetime.now(ZoneInfo("Europe/Oslo"))
        
        posts = data.get('posts', [])
        if not posts:
            logger.warning("No posts found in data")
            return []
        
        total_posts = len(posts)
        logger.info(f"Processing {total_posts} posts from Facebook")
        
        # Get all existing post URLs from database
        with db.session() as session:
            existing_urls = {post.post_url for post in session.query(ScrapedPost).all()}
        
        # Filter out posts that have already been processed
        posts_to_process = []
        skipped_posts = []
        
        for post in posts:
            post_url = post.get('url', '')
            if post_url in existing_urls:
                skipped_posts.append(post)
            else:
                posts_to_process.append(post)
        
        if skipped_posts:
            logger.info(f"Skipping {len(skipped_posts)} already processed posts")
        
        if not posts_to_process:
            logger.info("No new posts to process")
            return []
        
        logger.info(f"Processing {len(posts_to_process)} new posts")
        
        # Split posts into two lists based on whether they contain Facebook Event links
        posts_with_event_links = []
        posts_without_event_links = []
        
        for post in posts_to_process:
            if _has_facebook_event(post):
                posts_with_event_links.append(post)
            else:
                posts_without_event_links.append(post)
        
        logger.info(f"Found {len(posts_with_event_links)} posts with Facebook Event links")
        
        # Store posts with event links
        posts_with_events_to_store = []
        for post in posts_with_event_links:
            post_url = post.get('url', '')
            if post_url:
                posts_with_events_to_store.append({
                    'post_url': post_url,
                    'event_status': 'contains-event',
                    'scraped_at': processing_start_time
                })
        
        if posts_with_events_to_store:
            _store_scraped_posts(posts_with_events_to_store)
        
        # Extract event URLs from posts with events
        event_urls = []
        for post in posts_with_event_links:
            event_urls.extend(_extract_facebook_event_links(post))
        
        # Remove duplicates while preserving order
        event_urls = list(dict.fromkeys(event_urls))
        
        # Trigger event scraping if we found any event URLs
        if event_urls:
            logger.info(f"Triggering scrape for {len(event_urls)} Facebook Events")
            scraper = FacebookEventScraper()
            if not scraper.initialize_data_fetch(event_urls):
                logger.error("Failed to trigger Facebook Event scraping")
        
        # If SKIP_LLM_INTERPRETATION is true, we're done here
        if SKIP_LLM_INTERPRETATION:
            logger.info("Skipping LLM interpretation of non-Event posts")
            return []
        
        # Process posts without Event links using LLM
        events: List[Event] = []
        posts_without_event_links_to_store = []
        
        for post in posts_without_event_links:
            try:
                # Skip posts without content
                if not post.get('content'):
                    continue
                
                content = f"{post.get('post_external_title', '')}\n\n{post.get('content', '')}"
                is_event, _ = is_event_post(
                    content=content,
                    post_date=post.get('date_posted'),
                    author=post.get('user_username_raw')
                )
                
                # Add post to storage list with its event status
                post_url = post.get('url', '')
                if post_url:
                    event_status = 'is-event-llm' if is_event else 'not-event-llm'
                    posts_without_event_links_to_store.append({
                        'post_url': post_url,
                        'event_status': event_status,
                        'scraped_at': processing_start_time
                    })
                
                if is_event:
                    event_details = parse_event_details(
                        content=content,
                        url=post_url,
                        post_date=post.get('date_posted'),
                        author=post.get('user_username_raw')
                    )
                    if event_details:
                        try:
                            event = _create_event_from_post(post, event_details)
                            if event:
                                events.append(event)
                        except ValueError as e:
                            logger.warning(f"Could not create event: {e}")
                    
            except Exception as e:
                logger.error(f"Failed to process post: {e}")
                continue
        
        # Store posts processed by LLM
        if posts_without_event_links_to_store:
            _store_scraped_posts(posts_without_event_links_to_store)
            logger.info(f"Stored {len(posts_without_event_links_to_store)} posts processed by LLM")
        
        logger.info(f"Successfully processed {len(events)} events from {len(posts_without_event_links)} non-Event posts")
        return events
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return []
