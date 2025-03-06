"""Utility functions for working with raw scrape data."""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func

from ..db import get_db, init_db
from ..models.raw_scrape_data import RawScrapeData
from .timezone import now_oslo

logger = logging.getLogger(__name__)

def get_facebook_post_urls(days: int = 1) -> List[str]:
    """
    Get URLs of Facebook posts from raw data for the specified number of days.
    
    Args:
        days: Number of days to look back (default: 1 for today only)
        
    Returns:
        List[str]: List of Facebook post URLs
    """
    # Initialize database
    init_db()
    
    db = get_db()
    try:
        # Get date range in Oslo timezone
        end_date = now_oslo().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Get all raw data entries for Facebook in the date range
        raw_data = db.query(RawScrapeData).filter(
            RawScrapeData.source == 'brightdata_facebook_group',
            RawScrapeData.processed == True,
            func.date(RawScrapeData.created_at) >= start_date,
            func.date(RawScrapeData.created_at) <= end_date
        ).all()
        
        # Extract URLs from raw data
        urls = []
        for entry in raw_data:
            if isinstance(entry.raw_data, list):
                for post in entry.raw_data:
                    if isinstance(post, dict) and 'url' in post:
                        urls.append(post['url'])
        
        logger.info(f"Found {len(urls)} Facebook post URLs from the last {days} days")
        return urls
        
    finally:
        db.close() 