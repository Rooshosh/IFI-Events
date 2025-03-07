#!/usr/bin/env python3

"""Script to migrate data from SQLite to PostgreSQL."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.models.event import Event
from src.db.model import Base

def migrate_data():
    """Migrate data from SQLite to PostgreSQL."""
    # Path to SQLite database
    sqlite_path = Path(__file__).parent.parent / 'data' / 'events.db'
    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url)

    # PostgreSQL connection (destination)
    if not os.environ.get('DATABASE_URL'):
        raise ValueError("DATABASE_URL environment variable is required")
    pg_url = os.environ['DATABASE_URL']
    pg_engine = create_engine(
        pg_url,
        connect_args={'sslmode': 'require'}
    )

    # Create tables in PostgreSQL if they don't exist
    Base.metadata.create_all(pg_engine)

    # Create sessions for both databases
    from sqlalchemy.orm import Session
    sqlite_session = Session(sqlite_engine)
    pg_session = Session(pg_engine)

    try:
        # Get all events from SQLite
        events = sqlite_session.query(Event).all()
        print(f"Found {len(events)} events in SQLite database")

        # Insert events into PostgreSQL
        for event in events:
            # Create a new Event instance with the same data
            # This ensures we don't carry over any SQLite-specific metadata
            event_data = {
                'title': event.title,
                'description': event.description,
                'start_time': event.start_time,
                'end_time': event.end_time,
                'location': event.location,
                'source_url': event.source_url,
                'source_name': event.source_name,
                'created_at': event.created_at,
                'fetched_at': event.fetched_at,
                'capacity': event.capacity,
                'spots_left': event.spots_left,
                'registration_opens': event.registration_opens,
                'registration_url': event.registration_url,
                'food': event.food,
                'attachment': event.attachment,
                'author': event.author
            }
            new_event = Event(**event_data)
            pg_session.add(new_event)

        # Commit the changes
        pg_session.commit()
        print("Successfully migrated all events to PostgreSQL")

    except Exception as e:
        print(f"Error during migration: {e}")
        pg_session.rollback()
        raise
    finally:
        sqlite_session.close()
        pg_session.close()

if __name__ == '__main__':
    migrate_data() 