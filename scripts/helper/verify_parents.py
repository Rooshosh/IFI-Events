#!/usr/bin/env python3
"""Script to verify parent-child relationships in the production database."""

import os
import psycopg2
from dotenv import load_dotenv

# Set environment to production before importing any modules
os.environ['ENVIRONMENT'] = 'production'

def verify_relationships():
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    print(f"\nConnecting to database: {db_url.replace('postgres://', '').split('@')[0].split(':')[0]}:***@{db_url.split('@')[1]}\n")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Query events with parent-child relationships
        cur.execute("""
            WITH related_events AS (
                SELECT id, title, source_name, parent_id
                FROM events
                WHERE parent_id IS NOT NULL
                UNION
                SELECT id, title, source_name, parent_id
                FROM events
                WHERE id IN (
                    SELECT parent_id FROM events WHERE parent_id IS NOT NULL
                )
            )
            SELECT id, title, source_name, parent_id
            FROM related_events
            ORDER BY COALESCE(parent_id, id), id;
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("No parent-child relationships found in the database.")
            return
            
        print("Parent-Child Relationships:")
        print("-" * 80)
        
        current_parent = None
        for row in results:
            id, title, source, parent_id = row
            
            if parent_id is None:  # This is a parent event
                print(f"\nParent Event (ID: {id}):")
                print(f"  Title: {title}")
                print(f"  Source: {source}")
                current_parent = id
            else:  # This is a child event
                if parent_id == current_parent:
                    print(f"  └─ Child Event (ID: {id}):")
                    print(f"     Title: {title}")
                    print(f"     Source: {source}")
        
        print("\n")
        
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    verify_relationships() 