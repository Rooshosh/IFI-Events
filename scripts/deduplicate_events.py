#!/usr/bin/env python3
"""
CLI script to run database deduplication.
This is a maintenance script that can be run periodically to clean up duplicate events.
"""

import argparse
import logging
import sys

from src.utils.logging_config import configure_logging
from helper.db_maintenance import deduplicate_database

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Deduplicate events in the database')
    parser.add_argument(
        '--source',
        help='Optional source name to limit deduplication scope',
        default=None
    )
    args = parser.parse_args()
    
    configure_logging()
    
    try:
        merge_count, merged_events = deduplicate_database(args.source)
        logger.info(f"Successfully merged {merge_count} duplicate events")
        logger.info(f"Database now contains {len(merged_events)} unique events")
        return 0
    except Exception as e:
        logger.error(f"Failed to deduplicate database: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 