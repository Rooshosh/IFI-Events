"""Database maintenance utilities.

This module contains utilities for database maintenance tasks like:
- Finding and merging duplicate events
- Database cleanup
- Data integrity checks
"""

import logging
from typing import List, Tuple, Optional
from datetime import datetime

from src.models.event import Event
from src.db import db, DatabaseError, with_retry
from src.utils.deduplication import are_events_duplicate, merge_events

logger = logging.getLogger(__name__)

def _find_and_merge_duplicates(events: List[Event]) -> Tuple[List[Event], int]:
    """Find and merge duplicates within a list of events."""
    merged_events = []
    duplicate_count = 0
    processed_ids = set()
    
    for i, event1 in enumerate(events):
        if event1.id in processed_ids:
            continue
            
        current_event = event1
        for j, event2 in enumerate(events[i+1:], i+1):
            if event2.id in processed_ids:
                continue
                
            if are_events_duplicate(current_event, event2):
                current_event = merge_events(current_event, event2)
                processed_ids.add(event2.id)
                duplicate_count += 1
                logger.info(f"Found duplicate: '{event2.title}' matches '{event1.title}'")
        
        merged_events.append(current_event)
        processed_ids.add(event1.id)
    
    return merged_events, duplicate_count

@with_retry()
def deduplicate_database(source_name: Optional[str] = None) -> Tuple[int, List[Event]]:
    """
    Find and merge duplicate events in the database.
    This is a write operation that modifies data, so we use retry logic.
    
    Args:
        source_name: Optional source name to limit deduplication scope
        
    Returns:
        Tuple of (number of merges performed, list of merged events)
        
    Raises:
        DatabaseError: If database operations fail
    """
    try:
        with db.session() as session:
            # Query existing events
            query = session.query(Event)
            if source_name:
                query = query.filter(Event.source_name == source_name)
            events = query.all()
            
            if not events:
                logger.info("No events found for deduplication")
                return 0, []
            
            # Find and merge duplicates (in-memory operation)
            unique_events, merge_count = _find_and_merge_duplicates(events)
            
            if merge_count > 0:
                # Delete all events and reinsert unique ones
                query.delete()
                for event in unique_events:
                    session.add(event)
                
                logger.info(f"Merged {merge_count} duplicate events")
            
            return merge_count, unique_events
            
    except Exception as e:
        logger.error(f"Error during database deduplication: {e}")
        raise DatabaseError(f"Failed to deduplicate database: {e}") from e 