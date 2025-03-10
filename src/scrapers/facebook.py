"""Scraper for Facebook group posts using BrightData's API."""

import logging
from typing import List, Optional, Dict, Any
import requests
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to Python path when running directly
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scrapers.base import AsyncScraper
from src.utils.fetched_raw_facebook_data_ids import get_facebook_post_urls

logger = logging.getLogger(__name__)

# Default BrightData configuration
DEFAULT_BRIGHTDATA_CONFIG = {
    'api_key': os.getenv('BRIGHTDATA_API_KEY'),
    'dataset_id': 'gd_lz11l67o2cb3r0lkj3',
    'group_url': 'https://www.facebook.com/groups/ifistudenter',
    'days_to_fetch': 20,  # Default to fetching just today's posts
    'num_of_posts': 200,  # Safety limit on number of posts to fetch
    'webhook_base_url': 'https://e5f0-193-157-238-49.ngrok-free.app',  # TODO: Update this when ngrok URL changes
    'webhook_endpoint': '/webhook/brightdata/facebook-group/results',
    'webhook_auth': os.getenv('BRIGHTDATA_AUTHORIZATION_HEADER'),
    'webhook_format': 'json',
    'webhook_uncompressed': True,
    'include_errors': True
}

class FacebookGroupScraper(AsyncScraper):
    """
    Scraper for Facebook group posts using BrightData's API.
    
    This scraper:
    1. Uses BrightData's 'Facebook - Posts by group URL' dataset to fetch posts
    2. Sends results to a configured webhook for processing
    
    Configuration:
        brightdata: API configuration for BrightData
            - api_key: Your BrightData API key (required)
            - dataset_id: The dataset ID to use
            - group_url: URL of the Facebook group to scrape
            - days_to_fetch: How many days of posts to fetch (default: 1)
            - num_of_posts: Maximum number of posts to fetch (default: 20)
            - webhook_base_url: Base URL for webhooks (update when ngrok changes)
            - webhook_endpoint: Webhook endpoint path
            - webhook_auth: Authorization header for webhook
            - webhook_format: Format of webhook data (default: json)
            - webhook_uncompressed: Whether to send uncompressed data (default: true)
            - include_errors: Whether to include errors in response (default: true)
    """
    
    def __init__(self, brightdata_config: Dict[str, Any] = None):
        """
        Initialize the scraper with optional configuration overrides.
        
        Args:
            brightdata_config: Override default BrightData settings
            
        Raises:
            ValueError: If required environment variables or configuration values are missing or invalid
        """
        # Initialize BrightData configuration
        self.brightdata_config = DEFAULT_BRIGHTDATA_CONFIG.copy()
        if brightdata_config:
            self.brightdata_config.update(brightdata_config)
        
        # Validate required environment variables
        if not self.brightdata_config['api_key']:
            raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
        if not self.brightdata_config['webhook_auth']:
            raise ValueError("BRIGHTDATA_AUTHORIZATION_HEADER environment variable is required")
        
        # Validate configuration values
        if not self.brightdata_config['group_url']:
            raise ValueError("group_url is required")
        if not self.brightdata_config['webhook_base_url']:
            raise ValueError("webhook_base_url is required")
        if not self.brightdata_config['webhook_endpoint']:
            raise ValueError("webhook_endpoint is required")
        if self.brightdata_config['days_to_fetch'] < 1:
            raise ValueError("days_to_fetch must be at least 1")
        if self.brightdata_config['num_of_posts'] < 1:
            raise ValueError("num_of_posts must be at least 1")
        
        # Set up BrightData API parameters
        self.base_url = "https://api.brightdata.com/datasets/v3"
        self.headers = {
            "Authorization": f"Bearer {self.brightdata_config['api_key']}",
            "Content-Type": "application/json",
        }
        self.group_url = self.brightdata_config['group_url']
        
        # Calculate date range
        self.end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.start_date = self.end_date - timedelta(days=self.brightdata_config['days_to_fetch'] - 1)
        
        # Format dates for API
        self.start_date_str = self.start_date.strftime('%Y-%m-%d')
        self.end_date_str = self.end_date.strftime('%Y-%m-%d')
    
    def name(self) -> str:
        """Return the name of the scraper"""
        return "Facebook (IFI-studenter)"
    
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
        # Get URLs from raw data
        urls = get_facebook_post_urls(start_date=self.start_date, end_date=self.end_date)
        
        # Extract post IDs from URLs
        post_ids = []
        for url in urls:
            post_id = self._extract_post_id(url)
            if post_id:
                post_ids.append(post_id)
        
        logger.info(f"Found {len(post_ids)} already processed posts to exclude")
        return post_ids
    
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
                "url": self.group_url,
                "start_date": self.start_date_str,
                "end_date": self.end_date_str,
                "num_of_posts": self.brightdata_config['num_of_posts'],
                "posts_to_not_include": posts_to_exclude
            }]
            
            logger.info(f"Scraping up to {self.brightdata_config['num_of_posts']} posts from {self.start_date_str} to {self.end_date_str}")
            if posts_to_exclude:
                logger.info(f"Excluding {len(posts_to_exclude)} already processed posts")
            
            # Prepare request parameters
            params = {
                "dataset_id": self.brightdata_config['dataset_id'],
                "include_errors": str(self.brightdata_config['include_errors']).lower(),
            }
            
            # Add webhook configuration
            webhook_url = f"{self.brightdata_config['webhook_base_url']}{self.brightdata_config['webhook_endpoint']}"
            params.update({
                "endpoint": webhook_url,
                "auth_header": self.brightdata_config['webhook_auth'],
                "format": self.brightdata_config['webhook_format'],
                "uncompressed_webhook": str(self.brightdata_config['webhook_uncompressed']).lower(),
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

def scrape_facebook_posts(days: int = 4):
    """
    Scrape Facebook posts from the last N days.
    
    Args:
        days: Number of days to look back
    """
    # Calculate date range in Oslo timezone
    end_date = now_oslo()
    start_date = end_date - timedelta(days=days)
    
    # Set end_date to end of day (23:59:59)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Get URLs of already processed posts
    processed_urls = get_facebook_post_urls(start_date=start_date, end_date=end_date)
    logger.info(f"Found {len(processed_urls)} already processed posts to exclude")
    
    # Initialize scraper
    scraper = FacebookGroupScraper()
    
    # Scrape new posts
    try:
        scraper.scrape_posts(start_date=start_date, end_date=end_date, exclude_urls=processed_urls)
    except Exception as e:
        logger.error(f"Failed to scrape Facebook posts: {str(e)}")
        raise

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run scraper
    scraper = FacebookGroupScraper()
    success = scraper.initialize_data_fetch()
    
    # Print results
    if success:
        print("\nScrape triggered successfully!")
        print("Results will be sent to the configured webhook.")
    else:
        print("\nFailed to trigger scrape.")
        print("Check the logs for more details.") 