#!/usr/bin/env python3
"""Script to copy data from production PostgreSQL database to a local backup file.

This script copies the exact database structure and data from the production PostgreSQL database
hosted on Supabase to a backup SQLite file in the data/backups directory, without relying on
local data models.
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import re
from typing import Dict, Any

from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.schema import CreateTable

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_postgres_to_sqlite(create_stmt: str) -> str:
    """Convert PostgreSQL CREATE TABLE statement to SQLite syntax."""
    # Remove PostgreSQL-specific parts
    replacements = {
        'TIMESTAMP WITHOUT TIME ZONE': 'TIMESTAMP',
        'TIMESTAMP WITH TIME ZONE': 'TIMESTAMP',
        'BOOLEAN': 'INTEGER',  # SQLite doesn't have a boolean type
        'CHARACTER VARYING': 'TEXT',
        'DOUBLE PRECISION': 'REAL',
    }
    
    stmt = create_stmt
    for pg_type, sqlite_type in replacements.items():
        stmt = stmt.replace(pg_type, sqlite_type)
    
    # Remove PostgreSQL-specific syntax
    stmt = re.sub(r'DEFAULT nextval\([^)]+\)', '', stmt)
    stmt = re.sub(r'::regclass', '', stmt)
    stmt = re.sub(r'VARCHAR(\(\d+\))?', 'TEXT', stmt)
    stmt = re.sub(r'CONSTRAINT \w+ ', '', stmt)
    stmt = re.sub(r'WITH\(.*\)', '', stmt)  # Remove storage parameters
    
    # Clean up any double spaces and extra whitespace
    stmt = re.sub(r'\s+', ' ', stmt)
    
    return stmt

def convert_value_for_sqlite(value: Any) -> Any:
    """Convert a PostgreSQL value to a SQLite-compatible value."""
    if value is None:
        return None
    elif isinstance(value, bool):
        return 1 if value else 0
    elif isinstance(value, (int, float, str)):
        return value
    elif isinstance(value, datetime):
        return value.isoformat()
    else:
        return str(value)

def copy_prod_to_backup():
    """Copy data from production PostgreSQL database to a backup SQLite file."""
    # Create backups directory if it doesn't exist
    backups_dir = Path(__file__).parent.parent.parent / 'data' / 'backups'
    backups_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backups_dir / f'events_prod_{timestamp}.db'
    
    # Get the PostgreSQL URL from environment
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        raise ValueError("DATABASE_URL environment variable must be set")
    
    # Create engines
    postgres_engine = create_engine(postgres_url)
    sqlite_engine = create_engine(f"sqlite:///{backup_path}")
    
    try:
        # Reflect the production database structure
        metadata = MetaData()
        metadata.reflect(bind=postgres_engine)
        
        # Log found tables
        logger.info(f"Found tables in production database: {metadata.tables.keys()}")
        
        # Create tables in SQLite with the same structure
        with sqlite_engine.connect() as sqlite_conn:
            for table_name, table in metadata.tables.items():
                try:
                    # Get the CREATE TABLE statement
                    create_table = CreateTable(table)
                    # Convert PostgreSQL syntax to SQLite
                    create_stmt = convert_postgres_to_sqlite(str(create_table))
                    logger.debug(f"Creating table with statement:\n{create_stmt}")
                    
                    # Execute the modified CREATE TABLE statement
                    sqlite_conn.execute(text(create_stmt))
                    logger.info(f"Created table {table_name} in backup database")
                    
                    # Copy data
                    with postgres_engine.connect() as postgres_conn:
                        # Fetch all data from the table
                        result = postgres_conn.execute(table.select())
                        data = result.mappings().all()
                        logger.info(f"Found {len(data)} rows in {table_name}")
                        
                        if data:
                            # Get column names
                            columns = [col.name for col in table.columns]
                            
                            # Prepare INSERT statement
                            column_list = ', '.join(columns)
                            placeholders = ', '.join([f':{col}' for col in columns])
                            insert_stmt = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
                            
                            # Insert data into SQLite
                            for i, row in enumerate(data, 1):
                                try:
                                    # Convert row to dict with SQLite-compatible values
                                    values = {
                                        col: convert_value_for_sqlite(row[col])
                                        for col in columns
                                    }
                                    sqlite_conn.execute(text(insert_stmt), values)
                                    
                                    # Log progress for large tables
                                    if i % 100 == 0:
                                        logger.info(f"Inserted {i}/{len(data)} rows into {table_name}")
                                        
                                except Exception as row_error:
                                    logger.error(f"Error inserting row {i} into {table_name}: {row_error}")
                                    logger.error(f"Problematic row data: {row}")
                                    continue
                            
                            sqlite_conn.commit()
                            logger.info(f"Finished copying {len(data)} rows to {table_name}")
                            
                except Exception as table_error:
                    logger.error(f"Error processing table {table_name}: {table_error}")
                    raise
                        
        logger.info(f"Successfully created backup at {backup_path}")
        
    except Exception as e:
        logger.error(f"Error during backup: {e}")
        # If backup failed, try to remove the incomplete file
        try:
            if backup_path.exists():
                backup_path.unlink()
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up failed backup file: {cleanup_error}")
        raise
    finally:
        postgres_engine.dispose()
        sqlite_engine.dispose()

if __name__ == "__main__":
    copy_prod_to_backup() 