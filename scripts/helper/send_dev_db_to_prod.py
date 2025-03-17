#!/usr/bin/env python3
"""Script to create and populate the production database from development database.

This script copies all events and scraped posts from the local SQLite development database
to the production PostgreSQL database hosted on Supabase.
"""

import argparse
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import make_transient

from src.models import Base
from src.models.event import Event
from src.models.raw_scrape_data import ScrapedPost
from src.config.environment import IS_PRODUCTION_ENVIRONMENT

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_data(replace: bool = False):
    """Copy data from development SQLite database to production PostgreSQL database.
    
    Args:
        replace: If True, will replace all existing data. If False, will upsert based on unique fields.
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
        
        if replace:
            # Clear all existing data if replace is True
            logger.info("Clearing all existing data from production database...")
            postgres_session.query(Event).delete()
            postgres_session.query(ScrapedPost).delete()
            postgres_session.commit()
            logger.info("Successfully cleared all existing data from production database")
        
        # Get all scraped posts from SQLite
        scraped_posts = sqlite_session.query(ScrapedPost).all()
        logger.info(f"Found {len(scraped_posts)} scraped posts in SQLite database")
        
        # Get all events from SQLite (no source filter)
        events: List[Event] = sqlite_session.query(Event).all()
        logger.info(f"Found {len(events)} total events in SQLite database")
        
        # Log event sources for verification
        event_sources = {}
        for event in events:
            source = event.source_name
            event_sources[source] = event_sources.get(source, 0) + 1
        logger.info("Events by source:")
        for source, count in event_sources.items():
            logger.info(f"  {source}: {count} events")
        
        # Close SQLite session after fetching data
        sqlite_session.close()
        sqlite_session = None
        
        # Make objects transient (detached from any session)
        for event in events:
            make_transient(event)
            # Reset the ID to let PostgreSQL generate a new one
            event.id = None
        for post in scraped_posts:
            make_transient(post)
        
        # Insert or update events into PostgreSQL
        try:
            for event in events:
                if replace:
                    postgres_session.add(event)
                else:
                    # Try to find existing event by source_url
                    existing = postgres_session.query(Event).filter(
                        Event.source_url == event.source_url
                    ).first()
                    
                    if existing:
                        # Update existing event
                        for key, value in event.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing, key, value)
                        logger.debug(f"Updated existing event: {event.source_url}")
                    else:
                        # Add new event
                        postgres_session.add(event)
                        logger.debug(f"Added new event: {event.source_url}")
            
            postgres_session.commit()
            logger.info("Successfully migrated all events to PostgreSQL")
        except Exception as e:
            logger.error(f"Error migrating events: {e}")
            postgres_session.rollback()
            raise
        
        # Insert or update scraped posts into PostgreSQL
        try:
            for post in scraped_posts:
                if replace:
                    postgres_session.add(post)
                else:
                    # Try to find existing post by post_url
                    existing = postgres_session.query(ScrapedPost).filter(
                        ScrapedPost.post_url == post.post_url
                    ).first()
                    
                    if existing:
                        # Update existing post
                        for key, value in post.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing, key, value)
                        logger.debug(f"Updated existing post: {post.post_url}")
                    else:
                        # Add new post
                        postgres_session.add(post)
                        logger.debug(f"Added new post: {post.post_url}")
            
            postgres_session.commit()
            logger.info("Successfully migrated scraped posts to PostgreSQL")
        except Exception as e:
            logger.error(f"Error migrating scraped posts: {e}")
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
        '--replace',
        action='store_true',
        help='Replace all existing data instead of upserting (NOT RECOMMENDED)'
    )
    args = parser.parse_args()
    
    if args.replace:
        response = input("WARNING: This will replace ALL existing data in the production database. Are you sure? (y/N): ")
        if response.lower() != 'y':
            logger.info("Operation cancelled")
            exit(0)
    
    migrate_data(replace=args.replace) 