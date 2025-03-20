"""Scraper for Facebook group posts using BrightData's API."""

import logging
from typing import List, Optional, Dict, Any
import requests
from datetime import datetime, timedelta
from sqlalchemy import func
import os

from src.scrapers.base import AsyncScraper
from src.db import db, DatabaseError
from src.models.raw_scrape_data import ScrapedPost
from src.utils.timezone import now_oslo
from src.config.external_services import get_brightdata_config
from src.config.environment import IS_PRODUCTION_ENVIRONMENT
from src.config.development import DEVELOPMENT_FORWARDED_URL

logger = logging.getLogger(__name__)

class FacebookGroupScraper(AsyncScraper):
    """
    Scraper for Facebook group posts using BrightData's API.
    
    This scraper:
    1. Uses BrightData's 'Facebook - Posts by group URL' dataset to fetch posts
    2. Sends results to a configured webhook for processing
    
    Configuration is loaded from src.config.external_services.brightdata
    """
    
    def __init__(self):
        """
        Initialize the scraper with configuration from brightdata.py.
        
        Raises:
            ValueError: If required configuration values are missing or invalid
        """
        super().__init__(source_id='facebook-post')
        
        # Scraper-specific configuration
        self.scraper_config = {
            # Webhook configuration
            'webhook_endpoint': '/webhook/brightdata/facebook-group/results',
            'webhook_format': 'json',
            'webhook_uncompressed': True,

            # Dataset configuration
            'dataset_id': 'gd_lz11l67o2cb3r0lkj3',  # Facebook - Posts by group URL dataset
            'group_url': 'https://www.facebook.com/groups/ifistudenter',
            'include_errors': True,

            # Fetch parameters
            'days_to_fetch': 1,
            'num_of_posts': 10,
        }
            
        # Initialize BrightData configuration
        self.brightdata_config = get_brightdata_config()
        
        # Set up BrightData API parameters
        self.base_url = self.brightdata_config['base_url']
        self.headers = {
            "Authorization": f"Bearer {self.brightdata_config['api_key']}",
            "Content-Type": self.brightdata_config['content_type'],
        }
        
        # Calculate date range
        self.end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.start_date = self.end_date - timedelta(days=self.scraper_config['days_to_fetch'] - 1)
        
        # Format dates for API
        self.start_date_str = self.start_date.strftime('%Y-%m-%d')
        self.end_date_str = self.end_date.strftime('%Y-%m-%d')
    
    def _get_webhook_url(self) -> str:
        """Get the webhook URL at runtime."""
        webhook_base_url = 'https://ifi-events-data-service.up.railway.app' if IS_PRODUCTION_ENVIRONMENT else DEVELOPMENT_FORWARDED_URL
        return f"{webhook_base_url}{self.scraper_config['webhook_endpoint']}"
    
    def _extract_post_id(self, url: str) -> Optional[str]:
        """Extract the post ID from a Facebook post URL."""
        if not url:
            return None
        try:
            return url.split('/posts/')[-1].strip('/')
        except Exception:
            logger.warning(f"Could not extract post ID from URL: {url}")
            return None
    
    def _get_excluded_post_ids(self) -> List[str]:
        """
        Get list of post IDs from raw data that we've already processed.
        
        Returns:
            List[str]: List of post IDs to exclude from scraping
        """
        try:
            with db.session() as session:
                # Get all posts within the date range
                query = session.query(ScrapedPost)
                query = query.filter(ScrapedPost.scraped_at >= self.start_date)
                query = query.filter(ScrapedPost.scraped_at <= self.end_date)
                
                posts = query.all()
                logger.info(f"Found {len(posts)} already processed posts")
                
                # Extract post IDs from URLs
                post_ids = []
                for post in posts:
                    post_id = self._extract_post_id(post.post_url)
                    if post_id:
                        post_ids.append(post_id)
                
                logger.info(f"Extracted {len(post_ids)} post IDs to exclude")
                return post_ids
                
        except Exception as e:
            logger.error(f"Error fetching processed post IDs: {e}")
            raise DatabaseError(f"Failed to fetch processed post IDs: {e}") from e
    
    def initialize_data_fetch(self) -> bool:
        """
        Trigger a new scrape of the Facebook group.
        Results will be sent to the configured webhook.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Get list of post IDs to exclude
            posts_to_exclude = self._get_excluded_post_ids()
            
            # Prepare request data
            data = [{
                "url": self.scraper_config['group_url'],
                "start_date": self.start_date_str,
                "end_date": self.end_date_str,
                "num_of_posts": self.scraper_config['num_of_posts'],
                "posts_to_not_include": posts_to_exclude
            }]
            
            logger.info(f"Scraping up to {self.scraper_config['num_of_posts']} posts from {self.start_date_str} to {self.end_date_str}")
            if posts_to_exclude:
                logger.info(f"Excluding {len(posts_to_exclude)} already processed posts")
            
            # Prepare request parameters
            params = {
                "dataset_id": self.scraper_config['dataset_id'],
                "include_errors": str(self.scraper_config['include_errors']).lower(),
            }
            
            # Add webhook configuration
            webhook_url = self._get_webhook_url()
            params.update({
                "endpoint": webhook_url,
                "auth_header": self.brightdata_config['webhook_auth'],
                "format": self.scraper_config['webhook_format'],
                "uncompressed_webhook": str(self.scraper_config['webhook_uncompressed']).lower(),
            })
            logger.info(f"Webhook configured to send results to: {webhook_url}")
            
            # Make the request
            response = requests.post(
                f"{self.base_url}/trigger",
                headers=self.headers,
                params=params,
                json=data
            )
            response.raise_for_status()
            
            logger.info("Successfully triggered scrape. Results will be sent to webhook.")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Other error: {str(e)}")
            return False