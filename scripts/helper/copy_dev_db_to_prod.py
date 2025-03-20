#!/usr/bin/env python3
"""Script to copy development database to production.

This script copies all data from the local SQLite development database
to the production PostgreSQL database. It assumes the production database
is empty and will create all necessary tables.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import logging
import os
from typing import List, Any, Dict

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

from src.models import Base
from src.models.event import Event
from src.models.raw_scrape_data import ScrapedPost
from src.db import Database, DatabaseConfig, DatabaseError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_dev_engine():
    """Create SQLAlchemy engine for development SQLite database."""
    sqlite_path = Path(__file__).parent.parent.parent / 'data' / 'events.db'
    return create_engine(f"sqlite:///{sqlite_path}")

def get_prod_engine():
    """Create SQLAlchemy engine for production PostgreSQL database."""
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        raise ValueError("DATABASE_URL environment variable must be set")
    
    # Test connection before proceeding
    engine = create_engine(postgres_url)
    try:
        with engine.connect() as conn:
            # Try a simple query to test permissions
            result = conn.execute(text("SELECT current_user, current_database()")).fetchone()
            logger.info(f"Connected to database as user: {result[0]}, database: {result[1]}")
            
            # Test if we can create tables
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_permissions (
                    id SERIAL PRIMARY KEY
                )
            """))
            conn.commit()
            
            # Clean up test table
            conn.execute(text("DROP TABLE test_permissions"))
            conn.commit()
            
            logger.info("Successfully tested database permissions")
    except Exception as e:
        logger.error(f"Failed to connect to production database: {str(e)}")
        raise ValueError(f"Database connection test failed: {str(e)}") from e
    
    return engine

def copy_table_data(
    dev_engine: Any,
    prod_engine: Any,
    table_name: str,
    session: Session
) -> int:
    """Copy data from one table in dev to prod."""
    try:
        # Get data from dev
        with dev_engine.connect() as dev_conn:
            result = dev_conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            
            if not rows:
                logger.info(f"No data to copy for table {table_name}")
                return 0
            
            # Get column names
            columns = result.keys()
            
            # Insert into prod
            with prod_engine.connect() as prod_conn:
                # Prepare INSERT statement
                column_list = ', '.join(columns)
                placeholders = ', '.join([f':{col}' for col in columns])
                insert_stmt = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
                
                # Insert each row
                for row in rows:
                    values = dict(zip(columns, row))
                    prod_conn.execute(text(insert_stmt), values)
                
                prod_conn.commit()
                logger.info(f"Copied {len(rows)} rows to {table_name}")
                return len(rows)
                
    except Exception as e:
        logger.error(f"Error copying table {table_name}: {e}")
        raise DatabaseError(f"Failed to copy table {table_name}") from e

def copy_dev_to_prod():
    """Copy all data from development to production database."""
    # Create engines
    logger.info("Creating database engines...")
    dev_engine = get_dev_engine()
    prod_engine = get_prod_engine()
    logger.info("Successfully created database engines")
    
    try:
        # Create tables in production
        logger.info("Creating tables in production database...")
        try:
            Base.metadata.create_all(prod_engine)
            logger.info("Successfully created tables")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise DatabaseError(f"Failed to create tables in production database: {str(e)}") from e
        
        # Get all tables from dev
        logger.info("Inspecting development database for tables...")
        inspector = inspect(dev_engine)
        tables = inspector.get_table_names()
        logger.info(f"Found tables: {tables}")
        
        # Copy data from each table
        total_rows = 0
        for table in tables:
            logger.info(f"Processing table: {table}")
            try:
                rows_copied = copy_table_data(dev_engine, prod_engine, table, None)
                total_rows += rows_copied
            except Exception as e:
                logger.error(f"Failed to copy table {table}: {str(e)}")
                raise DatabaseError(f"Failed to copy table {table}: {str(e)}") from e
        
        logger.info(f"Successfully copied {total_rows} total rows to production database")
        
    except Exception as e:
        logger.error(f"Error during database copy: {e}")
        raise
    finally:
        dev_engine.dispose()
        prod_engine.dispose()
        logger.info("Database connections closed")

if __name__ == "__main__":
    response = input("WARNING: This will copy ALL data from development to production database. Are you sure? (y/N): ")
    if response.lower() != 'y':
        logger.info("Operation cancelled")
        exit(0)
    
    copy_dev_to_prod()
