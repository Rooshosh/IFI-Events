#!/usr/bin/env python3
"""Migration script to add parent_id column to events table."""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

def run_migration():
    """Add parent_id column to events table."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Create the migration
        print("Adding parent_id column to events table...")
        cur.execute("""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS parent_id INTEGER,
            ADD CONSTRAINT fk_parent
            FOREIGN KEY (parent_id) 
            REFERENCES events (id)
            ON DELETE SET NULL;
        """)

        # Commit the transaction
        conn.commit()
        print("Migration completed successfully!")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    run_migration() 