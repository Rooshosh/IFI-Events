"""Processor for Facebook group posts from BrightData."""

import logging
from typing import Dict, Any, List
from datetime import datetime
import json
from zoneinfo import ZoneInfo

from src.processors.base import DataProcessor
from src.models.event import Event
from src.utils.timezone import now_oslo

logger = logging.getLogger(__name__)

class FacebookProcessor(DataProcessor):
    """
    Processor for Facebook group posts from BrightData.
    
    This processor converts Facebook group posts into our Event model format.
    It handles the specific data structure and validation for Facebook posts.
    """
    
    def name(self) -> str:
        """Return the name of the processor"""
        return "facebook"
    
    def _parse_post_date(self, date_str: str) -> datetime:
        """Parse a post's date string into a datetime object"""
        try:
            # Example format: "2024-03-19T14:30:00"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.astimezone(ZoneInfo("Europe/Oslo"))
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            raise
    
    def _create_event_from_post(self, post: Dict[str, Any]) -> Event:
        """Convert a Facebook post into an Event object"""
        try:
            # Extract post data
            title = post.get('title', 'Facebook Post')
            description = post.get('description', '')
            post_date = self._parse_post_date(post.get('date', ''))
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
    
    def process_data(self, data: Dict[str, Any]) -> List[Event]:
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
                    event = self._create_event_from_post(post)
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