"""Example usage of the database implementation.

This module provides examples of how to properly use the database functionality.
It serves as both documentation and a reference for common patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.event import Event
from ..models.raw_scrape_data import RawScrapeData
from . import db, with_retry, execute_in_transaction, DatabaseError

logger = logging.getLogger(__name__)

# Example 1: Basic Session Usage
def get_all_events() -> List[Event]:
    """Example of basic session usage with the context manager."""
    with db.session() as session:
        return session.query(Event).all()

# Example 2: Using Retry Logic
@with_retry(max_attempts=3)
def get_event_by_id(event_id: int) -> Optional[Event]:
    """Example of using retry logic for potentially failing operations."""
    with db.session() as session:
        return session.query(Event).get(event_id)

# Example 3: Complex Transaction
def update_event_title(session: Session, event_id: int, new_title: str) -> Event:
    """Example of a transaction operation to be used with execute_in_transaction."""
    event = session.query(Event).get(event_id)
    if not event:
        raise DatabaseError(f"Event with ID {event_id} not found")
    
    event.title = new_title
    return event

# Example 4: Combining Transaction and Retry
def safe_update_event(event_id: int, new_title: str) -> Event:
    """Example of combining transaction execution with retry logic."""
    return execute_in_transaction(
        update_event_title,
        event_id=event_id,
        new_title=new_title
    )

# Example 5: Multiple Operations in One Transaction
def create_event_with_raw_data(
    title: str,
    start_time: datetime,
    raw_data: dict
) -> Event:
    """Example of performing multiple operations in a single transaction."""
    with db.session() as session:
        # Create the event
        event = Event(
            title=title,
            start_time=start_time,
            source_name="example"
        )
        session.add(event)
        
        # Create associated raw data
        raw_data_entry = RawScrapeData(
            source="example",
            raw_data=raw_data,
            created_at=datetime.utcnow()
        )
        session.add(raw_data_entry)
        
        # Both will be committed together
        return event

# Example 6: Complex Queries
def get_upcoming_events(limit: int = 10) -> List[Event]:
    """Example of more complex query operations."""
    with db.session() as session:
        return (
            session.query(Event)
            .filter(Event.start_time > datetime.utcnow())
            .order_by(Event.start_time.asc())
            .limit(limit)
            .all()
        )

# Example 7: Raw SQL When Needed
def get_random_event() -> Optional[Event]:
    """Example of using raw SQL when needed."""
    with db.session() as session:
        # Use SQLite's random() function
        return session.query(Event).order_by(text('RANDOM()')).first()

# Example 8: Bulk Operations
def bulk_update_source(old_source: str, new_source: str) -> int:
    """Example of bulk update operation."""
    with db.session() as session:
        return (
            session.query(Event)
            .filter(Event.source_name == old_source)
            .update(
                {Event.source_name: new_source},
                synchronize_session=False
            )
        )

# Example 9: Error Handling
def safe_create_event(title: str, start_time: datetime) -> Optional[Event]:
    """Example of proper error handling."""
    try:
        with db.session() as session:
            event = Event(
                title=title,
                start_time=start_time,
                source_name="example"
            )
            session.add(event)
            return event
    except DatabaseError as e:
        logger.error(f"Failed to create event: {e}")
        return None

# Usage examples
if __name__ == "__main__":
    # These examples won't actually run, they're just for demonstration
    
    # Basic query
    all_events = get_all_events()
    
    # Get single event with retry
    event = get_event_by_id(123)
    
    # Update with transaction
    updated_event = safe_update_event(123, "New Title")
    
    # Complex operation
    new_event = create_event_with_raw_data(
        title="Example Event",
        start_time=datetime.utcnow(),
        raw_data={"source": "example", "data": "value"}
    )
    
    # Complex query
    upcoming = get_upcoming_events(limit=5)
    
    # Bulk operation
    updated_count = bulk_update_source("old_source", "new_source") 