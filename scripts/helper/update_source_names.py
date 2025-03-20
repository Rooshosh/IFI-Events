#!/usr/bin/env python3
"""Script to update source names in the database to match the config."""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_source_names():
    """Update source names to match the config."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        return

    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Show current state
        cur.execute("""
            SELECT source_name, COUNT(*) as count
            FROM events 
            GROUP BY source_name
            ORDER BY count DESC;
        """)
        print("\nCurrent source names:")
        print("-" * 50)
        for row in cur.fetchall():
            print(f"{row[0]:<30} {row[1]:<10}")

        # Update the source names
        updates = [
            ("Facebook (IFI-studenter)", "Facebook Post"),
            ("Facebook Events", "Facebook Event")
        ]

        for old_name, new_name in updates:
            cur.execute("""
                WITH updated AS (
                    UPDATE events 
                    SET source_name = %s 
                    WHERE source_name = %s
                    RETURNING 1
                )
                SELECT COUNT(*) FROM updated;
            """, (new_name, old_name))
            count = cur.fetchone()[0]
            print(f"\nUpdated {count} events from '{old_name}' to '{new_name}'")

        # Show new state
        cur.execute("""
            SELECT source_name, COUNT(*) as count
            FROM events 
            GROUP BY source_name
            ORDER BY count DESC;
        """)
        print("\nUpdated source names:")
        print("-" * 50)
        for row in cur.fetchall():
            print(f"{row[0]:<30} {row[1]:<10}")

        # Commit the changes
        conn.commit()
        print("\nChanges committed successfully!")

    except Exception as e:
        print(f"Error updating source names: {e}")
        conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    update_source_names() 