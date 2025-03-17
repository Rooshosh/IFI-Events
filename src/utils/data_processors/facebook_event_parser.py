"""Processor for Facebook Event raw data.

This module processes raw Facebook Event data from BrightData's API
to extract event information and create Event objects.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.models.event import Event

logger = logging.getLogger(__name__)

def _parse_event_date(date_str: str) -> Optional[datetime]:
    """
    Parse an event's date string into a datetime object.
    
    Args:
        date_str: Date string to parse (e.g., "2017-11-03T17:00:00.000Z")
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
        
    try:
        # Parse ISO format and convert to Oslo timezone
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.astimezone(ZoneInfo("Europe/Oslo"))
    except ValueError:
        logger.warning(f"Could not parse date string: {date_str}")
        return None

def _create_event_from_data(event_data: Dict[str, Any]) -> Optional[Event]:
    """
    Convert Facebook Event data into an Event object.
    
    Args:
        event_data: Raw event data from Facebook
        
    Returns:
        Optional[Event]: Event object if successful, None otherwise
    """
    try:
        # Get required fields with better error messages
        title = event_data.get('title')
        if not title:
            logger.warning("Skipping event: Missing title")
            return None
            
        # Get start time (required)
        event_date = event_data.get('event_date')
        if not event_date:
            logger.warning(f"Skipping event '{title}': Missing event_date")
            return None
            
        start_time = _parse_event_date(event_date)
        if not start_time:
            logger.warning(f"Skipping event '{title}': Invalid event_date format")
            return None
            
        # Get description - handle nested structure
        description = ''
        desc_data = event_data.get('description')
        if isinstance(desc_data, dict):
            description = desc_data.get('text', '')
        elif isinstance(desc_data, str):
            description = desc_data
        
        # Get location - handle nested structure safely
        location = None
        loc_data = event_data.get('location')
        if isinstance(loc_data, dict):
            location = loc_data.get('address')
        
        # Get end time (only if duration is valid)
        end_time = None
        duration_data = event_data.get('duration')
        if isinstance(duration_data, dict) and duration_data.get('time_units') and duration_data.get('time'):
            try:
                duration_minutes = int(duration_data['time'])
                if duration_minutes > 0:
                    end_time = start_time + timedelta(minutes=duration_minutes)
            except (ValueError, TypeError):
                logger.debug(f"Could not calculate end time for event '{title}': Invalid duration")
        
        # Get URL
        url = event_data.get('url', '')
        
        # Get author (from event_by or hosts) - handle nested structure
        author = None
        event_by = event_data.get('event_by', [])
        hosts = event_data.get('hosts', [])
        
        if isinstance(event_by, list) and event_by:
            author = event_by[0].get('name')
        elif isinstance(hosts, list) and hosts:
            author = hosts[0].get('name')
        
        # Get attachment (main image)
        attachment = event_data.get('main_image_downloadable')
        
        # Create event
        event = Event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,  # Will be None if duration was invalid or missing
            location=location,
            source_url=url,
            source_name="Facebook Events",
            fetched_at=datetime.now(ZoneInfo("Europe/Oslo")),
            author=author,
            attachment=attachment
        )
        
        return event
        
    except Exception as e:
        logger.error(f"Error creating event from data: {str(e)}", exc_info=True)
        return None

def parse_facebook_events(data: Dict[str, Any]) -> List[Event]:
    """
    Process raw Facebook Event data to extract events.
    
    Args:
        data: Raw data from Facebook Event scrape
        
    Returns:
        List[Event]: List of extracted events
    """
    try:
        # Handle both list and dict responses
        events_data = data if isinstance(data, list) else data.get('events', [])
        if not events_data:
            logger.warning("No events found in data")
            return []
        
        total_events = len(events_data)
        logger.info(f"Processing {total_events} events from Facebook")
        
        # Process each event
        events: List[Event] = []
        for event_data in events_data:
            try:
                # Log event details before processing
                logger.debug(f"Processing event: {event_data.get('title', 'Unknown Title')}")
                logger.debug(f"Event data: {event_data}")
                
                event = _create_event_from_data(event_data)
                if event:
                    events.append(event)
                    logger.debug(f"Successfully created event: {event.title}")
                else:
                    logger.warning(f"Failed to create event from data: {event_data.get('title', 'Unknown Title')}")
            except Exception as e:
                logger.error(f"Failed to process event: {e}", exc_info=True)
                logger.error(f"Event data that caused error: {event_data}")
                continue
        
        logger.info(f"Successfully processed {len(events)} events")
        return events
        
    except Exception as e:
        logger.error(f"Error processing data: {e}", exc_info=True)
        return [] 