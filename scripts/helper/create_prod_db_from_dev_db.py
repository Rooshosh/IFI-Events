#!/usr/bin/env python3
"""Script to copy development database to production.

This script drops all tables in production and recreates them with data from development.
"""

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from src.models import Base
from src.config.environment import IS_PRODUCTION_ENVIRONMENT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def copy_dev_to_prod():
    """Copy development database to production by dropping and recreating tables."""
    # Get the SQLite database path
    sqlite_path = Path(__file__).parent.parent.parent / 'data' / 'events.db'
    
    # Get the PostgreSQL URL from environment
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        raise ValueError("DATABASE_URL environment variable must be set")
    
    # Create engines
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    postgres_engine = create_engine(postgres_url)
    
    try:
        # Drop all tables in production
        logger.info("Dropping all tables in production database...")
        Base.metadata.drop_all(postgres_engine)
        logger.info("Successfully dropped all tables")
        
        # Create tables in production
        logger.info("Creating tables in production database...")
        Base.metadata.create_all(postgres_engine)
        logger.info("Successfully created tables")
        
        # Copy data from SQLite to PostgreSQL
        logger.info("Copying data from development to production...")
        
        # Get all tables
        inspector = inspect(sqlite_engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            # Get data from SQLite
            with sqlite_engine.connect() as sqlite_conn:
                result = sqlite_conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                
                if rows:
                    # Get column names
                    columns = result.keys()
                    
                    # Insert into PostgreSQL
                    with postgres_engine.connect() as postgres_conn:
                        # Prepare INSERT statement
                        column_list = ', '.join(columns)
                        placeholders = ', '.join([f':{col}' for col in columns])
                        insert_stmt = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                        
                        # Insert each row
                        for row in rows:
                            values = dict(zip(columns, row))
                            postgres_conn.execute(text(insert_stmt), values)
                        
                        postgres_conn.commit()
                        logger.info(f"Copied {len(rows)} rows to {table}")
        
        logger.info("Successfully copied all data to production database")
        
    except Exception as e:
        logger.error(f"Error during database copy: {e}")
        raise
    finally:
        sqlite_engine.dispose()
        postgres_engine.dispose()

if __name__ == "__main__":
    response = input("WARNING: This will delete ALL existing data from the production database. Are you sure? (y/N): ")
    if response.lower() != 'y':
        logger.info("Operation cancelled")
        exit(0)
    
    copy_dev_to_prod() 