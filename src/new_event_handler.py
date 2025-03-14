"""Handler for processing new event data from scrapers."""

import logging
from typing import List, Optional, Tuple
from datetime import datetime

from .models.event import Event
from .db import db, DatabaseError, with_retry
from .utils.deduplication import (
    merge_events,
    check_duplicate_before_insert
)

logger = logging.getLogger(__name__)

@with_retry()
def process_new_events(
    events: List[Event],
    source_name: str,
    skip_merging: bool = False
) -> Tuple[int, int]:
    """
    Process a list of new events, handling duplicates and database storage.
    
    This is a write operation that modifies the database, so we use retry logic.
    
    Args:
        events: List of events to process
        source_name: Source of the events (for logging and duplicate checking)
        skip_merging: If True, events will be inserted without duplicate checking
        
    Returns:
        Tuple of (new events added, events updated)
        
    Raises:
        DatabaseError: If database operations fail
    """
    if not events:
        logger.info("No events to process")
        return 0, 0
    
    new_count = 0
    update_count = 0
    
    try:
        with db.session() as session:
            for event in events:
                # Set source name if not already set
                if not event.source_name:
                    event.source_name = source_name
                
                if skip_merging:
                    session.add(event)
                    new_count += 1
                    continue
                
                # Check for duplicates
                existing_event = check_duplicate_before_insert(event, session)
                
                if existing_event:
                    # Merge and update existing event
                    merged_event = merge_events(existing_event, event)
                    # Update its attributes
                    for key, value in merged_event.__dict__.items():
                        if not key.startswith('_'):
                            setattr(existing_event, key, value)
                    update_count += 1
                    logger.info(f"Updated existing event: {existing_event.title}")
                else:
                    # Add new event
                    session.add(event)
                    new_count += 1
                    logger.info(f"Added new event: {event.title}")
            
            logger.info(f"Processed {len(events)} events: {new_count} new, {update_count} updated")
            return new_count, update_count
            
    except Exception as e:
        logger.error(f"Error processing events: {e}")
        raise DatabaseError(f"Failed to process events: {e}") from e 