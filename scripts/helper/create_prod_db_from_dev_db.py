#!/usr/bin/env python3
"""Script to create and populate the production database from development database.

This script copies all events and raw data from the local SQLite development database
to the production PostgreSQL database hosted on Supabase.
"""

import argparse
import logging
import os
from pathlib import Path
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import make_transient

from src.models import Base
from src.models.event import Event
from src.models.raw_scrape_data import RawScrapeData
from src.config.environment import IS_PRODUCTION_ENVIRONMENT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_data(clear_existing: bool = False):
    """Copy data from development SQLite database to production PostgreSQL database.
    
    Args:
        clear_existing: If True, will delete all existing data from production database before copying
    """
    # Get the SQLite database path (adjusted for helper folder location)
    sqlite_path = Path(__file__).parent.parent.parent / 'data' / 'events.db'
    
    # Get the PostgreSQL URL from environment
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        raise ValueError("DATABASE_URL environment variable must be set")
    
    # Create SQLite engine
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    
    # Create PostgreSQL engine
    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = None
    postgres_session = None
    
    try:
        sqlite_session = SQLiteSession()
        postgres_session = PostgresSession()
        
        # Ensure tables exist in PostgreSQL
        Base.metadata.create_all(postgres_engine)
        
        # Always clear raw data as we want to replace it completely
        logger.info("Clearing existing raw data from production database...")
        postgres_session.query(RawScrapeData).delete()
        postgres_session.commit()
        logger.info("Successfully cleared existing raw data from production database")
        
        # Get all raw data from SQLite
        raw_data = sqlite_session.query(RawScrapeData).all()
        logger.info(f"Found {len(raw_data)} raw data entries in SQLite database")
        
        # Get all Facebook events from SQLite
        events: List[Event] = sqlite_session.query(Event).filter(
            Event.source_name == "Facebook (IFI-studenter)"
        ).all()
        logger.info(f"Found {len(events)} Facebook events in SQLite database")
        
        # Close SQLite session after fetching data
        sqlite_session.close()
        sqlite_session = None
        
        # Make objects transient (detached from any session)
        for event in events:
            make_transient(event)
            # Reset the ID to let PostgreSQL generate a new one
            event.id = None
        for data in raw_data:
            make_transient(data)
        
        # Insert events into PostgreSQL
        try:
            for event in events:
                postgres_session.add(event)
            postgres_session.commit()
            logger.info("Successfully migrated Facebook events to PostgreSQL")
        except Exception as e:
            logger.error(f"Error migrating events: {e}")
            postgres_session.rollback()
            raise
        
        # Insert raw data into PostgreSQL
        try:
            for data in raw_data:
                postgres_session.add(data)
            postgres_session.commit()
            logger.info("Successfully migrated raw data to PostgreSQL")
        except Exception as e:
            logger.error(f"Error migrating raw data: {e}")
            postgres_session.rollback()
            raise
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        if postgres_session:
            postgres_session.rollback()
        raise
    finally:
        if sqlite_session:
            sqlite_session.close()
        if postgres_session:
            postgres_session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--clear-existing',
        action='store_true',
        help='Clear ALL existing data from production database before copying (NOT RECOMMENDED)'
    )
    args = parser.parse_args()
    
    if args.clear_existing:
        response = input("WARNING: This will delete ALL existing data from the production database. Are you sure? (y/N): ")
        if response.lower() != 'y':
            logger.info("Operation cancelled")
            exit(0)
    
    migrate_data(clear_existing=args.clear_existing) 