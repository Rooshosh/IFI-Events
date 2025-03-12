from datetime import datetime, timedelta
import logging
from typing import Optional, List, Tuple, Any, Dict, Callable
from difflib import SequenceMatcher
from ..models.event import Event
from ..db import db, DatabaseError, with_retry

logger = logging.getLogger(__name__)

# Deduplication configuration constants
TITLE_SIMILARITY_THRESHOLD = 0.85  # How similar titles need to be (0-1)
TIME_WINDOW_MINUTES = 120  # How close in time events need to be
REQUIRE_SAME_LOCATION = False  # Whether location must match
REQUIRE_EXACT_TIME = False  # Whether times must match exactly
IGNORE_CASE = True  # Whether to ignore case in string comparisons
NORMALIZE_WHITESPACE = True  # Whether to normalize whitespace in strings
REQUIRE_SAME_SOURCE = True  # Whether events must be from the same source

def normalize_string(text: str) -> str:
    """Normalize string based on configuration constants"""
    if not text:
        return ""
    if IGNORE_CASE:
        text = text.lower()
    if NORMALIZE_WHITESPACE:
        text = ' '.join(text.split())
    return text

def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles.
    Currently uses a simple ratio, but could be enhanced with better algorithms.
    """
    title1 = normalize_string(title1)
    title2 = normalize_string(title2)
    
    return SequenceMatcher(None, title1, title2).ratio()

def are_events_duplicate(event1: Event, event2: Event) -> bool:
    """
    Check if two events are duplicates based on configured thresholds.
    Returns True if events are considered duplicates, False otherwise.
    """
    # Check source if required
    if REQUIRE_SAME_SOURCE:
        if not event1.source_name or not event2.source_name or event1.source_name != event2.source_name:
            return False
    
    # Check title similarity
    title_similarity = calculate_title_similarity(event1.title, event2.title)
    if title_similarity < TITLE_SIMILARITY_THRESHOLD:
        return False
    
    # Check times
    if REQUIRE_EXACT_TIME:
        if event1.start_time != event2.start_time or event1.end_time != event2.end_time:
            return False
    else:
        time_window = timedelta(minutes=TIME_WINDOW_MINUTES)
        if abs(event1.start_time - event2.start_time) > time_window:
            return False
    
    # Check location if required
    if REQUIRE_SAME_LOCATION:
        loc1 = normalize_string(event1.location or "")
        loc2 = normalize_string(event2.location or "")
        if loc1 != loc2:
            return False
    
    return True

# Special merge strategies for specific fields
EVENT_MERGE_STRATEGIES: Dict[str, Callable[[Event, Event], Any]] = {
    'id': lambda e1, e2: e1.id or e2.id,  # Always keep an existing ID, never None
    'description': lambda e1, e2: (
        f"{e1.description}\n\nAlternative description:\n{e2.description}"
        if (e2.description and e2.description != e1.description)
        else e1.description
    ),
    'start_time': lambda e1, e2: min(e1.start_time, e2.start_time),
    'end_time': lambda e1, e2: max(e1.end_time, e2.end_time) if (e1.end_time and e2.end_time) else (e1.end_time or e2.end_time),
    'created_at': lambda e1, e2: min(e1.created_at, e2.created_at) if (e1.created_at and e2.created_at) else (e1.created_at or e2.created_at),
    'registration_opens': lambda e1, e2: min(e1.registration_opens, e2.registration_opens) if (e1.registration_opens and e2.registration_opens) else (e1.registration_opens or e2.registration_opens),
    'source_name': lambda e1, e2: (
        # If both events have the same source, keep it
        e1.source_name if e1.source_name == e2.source_name
        # If only one has a source, use that one
        else (e1.source_name or e2.source_name)
    ),
    'attachment': lambda e1, e2: (
        # Keep the attachment from the newer event if it has one, otherwise keep the older one
        e2.attachment if e2.attachment else e1.attachment
    ),
    'author': lambda e1, e2: (
        f"{e1.author}, {e2.author}"
        if (e1.author and e2.author and e1.author != e2.author)
        else (e1.author or e2.author)
    )
}

def merge_events(event1: Event, event2: Event) -> Event:
    """
    Merge two events, keeping the most complete information.
    The first event is considered primary and its values are kept in case of conflicts.
    """
    # Determine which event is newer
    event1_time = event1.fetched_at or datetime.min.replace(tzinfo=event1.start_time.tzinfo)
    event2_time = event2.fetched_at or datetime.min.replace(tzinfo=event2.start_time.tzinfo)
    
    # Create a copy of the newer event as the base
    base_event = event2 if event2_time > event1_time else event1
    other_event = event1 if event2_time > event1_time else event2
    
    # Preserve source_name if both events are from the same source
    source_name = None
    if base_event.source_name == other_event.source_name:
        source_name = base_event.source_name
    
    # Apply special merge strategies
    for field, strategy in EVENT_MERGE_STRATEGIES.items():
        try:
            merged_value = strategy(base_event, other_event)
            setattr(base_event, field, merged_value)
        except Exception as e:
            logger.warning(f"Failed to apply merge strategy for {field}: {e}")
    
    # Ensure source_name is preserved if both events were from the same source
    if source_name:
        base_event.source_name = source_name
    
    return base_event

def check_duplicate_before_insert(new_event: Event) -> Optional[Event]:
    """
    Check if an event already exists in the database.
    This is a read-only operation, so no retry needed.
    
    Args:
        new_event: Event to check for duplicates
        
    Returns:
        Matching event if found, None otherwise
        
    Raises:
        DatabaseError: If database query fails
    """
    try:
        with db.session() as session:
            # Get potential duplicates based on time window
            time_window = timedelta(minutes=TIME_WINDOW_MINUTES)
            start_time = new_event.start_time - time_window
            end_time = new_event.start_time + time_window
            
            query = session.query(Event).filter(
                Event.start_time.between(start_time, end_time)
            )
            
            if REQUIRE_SAME_SOURCE:
                query = query.filter(Event.source_name == new_event.source_name)
            
            potential_duplicates = query.all()
            
            # Check each potential duplicate
            for existing_event in potential_duplicates:
                if are_events_duplicate(new_event, existing_event):
                    logger.info(f"Found duplicate event: {existing_event.title}")
                    return existing_event
            
            return None
            
    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        raise DatabaseError(f"Failed to check for duplicates: {e}") from e 