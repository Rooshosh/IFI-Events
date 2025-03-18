"""Handler for processing new event data from scrapers."""

import logging
from typing import List, Optional, Tuple
from datetime import datetime

from .models.event import Event
from .db import db, DatabaseError, with_retry
from .utils.deduplication import (
    merge_events,
    check_duplicate_before_insert,
    are_events_cross_source_duplicate
)
from sqlalchemy.orm import Session
from .config.data_sources import compare_source_priorities

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
                    
                    # Check for duplicates from other sources
                    check_and_process_cross_source_duplicates(event, session)
            
            logger.info(f"Processed {len(events)} events: {new_count} new, {update_count} updated")
            return new_count, update_count
            
    except Exception as e:
        logger.error(f"Error processing events: {e}")
        raise DatabaseError(f"Failed to process events: {e}") from e


def check_and_process_cross_source_duplicates(new_event: Event, session: Session):
    """
    Check for duplicates from other sources and process them.
    """
    potential_duplicates = session.query(Event).filter(Event.id != new_event.id).all()
    for existing_event in potential_duplicates:
        if are_events_cross_source_duplicate(new_event, existing_event):
            process_cross_source_duplicate(new_event, existing_event, session)


def process_cross_source_duplicate(event1: Event, event2: Event, session: Session):
    """
    Process a duplicate event from another source by comparing source priorities.
    """
    higher_priority_event, lower_priority_event = compare_source_priority(event1, event2)
    
    # Find the topmost parent
    topmost_parent = higher_priority_event
    while topmost_parent.parent_id is not None:
        topmost_parent = session.query(Event).get(topmost_parent.parent_id)
    
    # Assign the topmost parent to the lower priority event
    lower_priority_event.parent_id = topmost_parent.id


def compare_source_priority(event1: Event, event2: Event) -> Tuple[Event, Event]:
    """
    Compare the priority of two event sources and return them in order of priority.
    """
    comparison = compare_source_priorities(event1.source_name, event2.source_name)
    return (event1, event2) if comparison >= 0 else (event2, event1) 