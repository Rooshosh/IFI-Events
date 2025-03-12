"""Example usage of the database implementation.

This module provides examples of how to properly use the database functionality.
It serves as both documentation and a reference for common patterns.

Environment Configuration:
- Development: Uses SQLite by default (no configuration needed)
- Production: Requires DATABASE_URL environment variable to be set
"""

import logging
from datetime import datetime
from typing import List, Optional
import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.event import Event
from ..models.raw_scrape_data import RawScrapeData
from . import db, with_retry, execute_in_transaction, DatabaseError, DatabaseConfig, Database

logger = logging.getLogger(__name__)

# Example 0: Database Configuration
def configure_database():
    """Example of different database configuration options."""
    # Default configuration (development with SQLite)
    default_db = Database()
    
    # Production configuration (using environment variable)
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
    prod_db = Database()
    
    # Custom configuration
    custom_config = DatabaseConfig(
        # URL provided directly instead of from environment
        postgres_url='postgresql://user:pass@host:5432/db',
        # Customize pool settings if needed
        pool_size=5,
        max_overflow=7
    )
    custom_db = Database(config=custom_config)

# Example 1: Basic Session Usage
def get_all_events() -> List[Event]:
    """Example of basic session usage with the context manager."""
    with db.session() as session:
        return session.query(Event).all()

# Example 2: Using Retry Logic for Network Operations
@with_retry(max_attempts=3)
def get_event_by_id(event_id: int) -> Optional[Event]:
    """Example of using retry logic for potentially failing operations."""
    with db.session() as session:
        return session.query(Event).get(event_id)

# Example 3: Complex Transaction with Error Handling
def update_event_title(session: Session, event_id: int, new_title: str) -> Event:
    """Example of a transaction operation to be used with execute_in_transaction."""
    event = session.query(Event).get(event_id)
    if not event:
        raise DatabaseError(f"Event with ID {event_id} not found")
    
    event.title = new_title
    return event

# Example 4: Safe Transaction Execution with Retry
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
        try:
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
            
            return event
        except Exception as e:
            # No need to explicitly rollback - the context manager handles it
            logger.error(f"Failed to create event with raw data: {e}")
            raise DatabaseError("Failed to create event with raw data") from e

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
        # Use database-appropriate random function
        if db.config.environment == "development":
            # SQLite
            return session.query(Event).order_by(text('RANDOM()')).first()
        else:
            # PostgreSQL
            return session.query(Event).order_by(text('random()')).first()

# Example 8: Bulk Operations
def bulk_update_source(old_source: str, new_source: str) -> int:
    """Example of bulk update operation."""
    with db.session() as session:
        try:
            count = (
                session.query(Event)
                .filter(Event.source_name == old_source)
                .update(
                    {Event.source_name: new_source},
                    synchronize_session=False
                )
            )
            return count
        except Exception as e:
            logger.error(f"Failed to perform bulk update: {e}")
            raise DatabaseError("Failed to update event sources") from e

# Example 9: Error Handling Best Practices
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
        logger.error(f"Database error creating event: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating event: {e}")
        return None

# Usage examples
if __name__ == "__main__":
    # These examples won't actually run, they're just for demonstration
    
    # Configure database based on environment
    if os.environ.get('ENVIRONMENT') == 'production':
        # Production uses PostgreSQL from DATABASE_URL
        db = Database()
    else:
        # Development uses SQLite
        db = Database()
    
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
    
    # Bulk operation with error handling
    try:
        updated_count = bulk_update_source("old_source", "new_source")
        logger.info(f"Updated {updated_count} events")
    except DatabaseError as e:
        logger.error(f"Failed to update sources: {e}") 