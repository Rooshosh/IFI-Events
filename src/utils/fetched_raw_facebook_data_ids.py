"""Utility functions for working with raw scrape data."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func

from ..db import get_db, init_db
from ..models.raw_scrape_data import RawScrapeData
from .timezone import now_oslo

logger = logging.getLogger(__name__)

def get_facebook_post_urls(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[str]:
    """
    Get URLs of Facebook posts from raw data within the specified date range.
    
    Args:
        start_date: Start date to look for posts (inclusive)
        end_date: End date to look for posts (inclusive)
        
    Returns:
        List[str]: List of Facebook post URLs
    """
    # Initialize database
    init_db()
    
    db = get_db()
    try:
        # Get all raw data entries for Facebook
        query = db.query(RawScrapeData).filter(
            RawScrapeData.source == 'brightdata_facebook_group',
            RawScrapeData.processed == True
        )
        
        # Apply date filters if provided
        if start_date:
            logger.info(f"Filtering posts created after {start_date}")
            query = query.filter(RawScrapeData.created_at >= start_date)
        if end_date:
            # Set end_date to end of day (23:59:59)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            logger.info(f"Filtering posts created before {end_date}")
            query = query.filter(RawScrapeData.created_at <= end_date)
        
        # Log the SQL query
        logger.info(f"SQL Query: {str(query)}")
        
        raw_data = query.all()
        logger.info(f"Found {len(raw_data)} raw data entries")
        
        # Extract URLs from raw data
        urls = []
        for entry in raw_data:
            if isinstance(entry.raw_data, dict):
                # Handle single post
                if 'url' in entry.raw_data:
                    urls.append(entry.raw_data['url'])
            elif isinstance(entry.raw_data, list):
                # Handle list of posts
                for post in entry.raw_data:
                    if isinstance(post, dict) and 'url' in post:
                        urls.append(post['url'])
        
        logger.info(f"Found {len(urls)} Facebook post URLs from raw data")
        return urls
        
    finally:
        db.close() 