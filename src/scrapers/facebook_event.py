"""Scraper for Facebook Events using BrightData's API."""

import logging
from typing import List, Optional, Dict, Any
import requests
from datetime import datetime
import os

from src.scrapers.base import AsyncScraper
from src.utils.timezone import now_oslo
from src.config.external_services import get_brightdata_config
from src.config.environment import IS_PRODUCTION_ENVIRONMENT

logger = logging.getLogger(__name__)

class FacebookEventScraper(AsyncScraper):
    """
    Scraper for Facebook Events using BrightData's API.
    
    This scraper:
    1. Uses BrightData's 'Facebook - Event by URL' dataset to fetch event details
    2. Sends results to a configured webhook for processing
    
    Configuration is loaded from src.config.external_services.brightdata
    """
    
    def __init__(self):
        """
        Initialize the scraper with configuration from brightdata.py.
        
        Raises:
            ValueError: If required configuration values are missing or invalid
        """
        # Scraper-specific configuration
        self.scraper_config = {
            # Webhook configuration
            'webhook_endpoint': '/webhook/brightdata/facebook-events/results',
            'webhook_format': 'json',
            'webhook_uncompressed': True,

            # Dataset configuration
            'dataset_id': 'gd_m14sd0to1jz48ppm51',  # Facebook - Event by URL dataset
            'include_errors': True,
        }
            
        # Initialize BrightData configuration
        self.brightdata_config = get_brightdata_config()
        
        # Set up BrightData API parameters
        self.base_url = self.brightdata_config['base_url']
        self.headers = {
            "Authorization": f"Bearer {self.brightdata_config['api_key']}",
            "Content-Type": self.brightdata_config['content_type'],
        }
    
    def _get_webhook_url(self) -> str:
        """Get the webhook URL at runtime."""
        webhook_base_url = 'https://ifi-events-data-service.up.railway.app' if IS_PRODUCTION_ENVIRONMENT else os.environ.get('NGROK_URL')
        if not webhook_base_url and not IS_PRODUCTION_ENVIRONMENT:
            raise ValueError("NGROK_URL environment variable must be set in development mode")
        return f"{webhook_base_url}{self.scraper_config['webhook_endpoint']}"
    
    def name(self) -> str:
        """Return the name of the scraper"""
        source_name = self.get_source_name()
        if not source_name:
            raise ValueError(f"No source name found for scraper {self.__class__.__name__}")
        return source_name
    
    def _extract_event_id(self, url: str) -> Optional[str]:
        """Extract the event ID from a Facebook event URL."""
        if not url:
            return None
        try:
            return url.split('/events/')[-1].strip('/')
        except Exception:
            logger.warning(f"Could not extract event ID from URL: {url}")
            return None
    
    def initialize_data_fetch(self, event_urls: List[str]) -> bool:
        """
        Trigger a new scrape of the specified Facebook Events.
        Results will be sent to the configured webhook.
        
        Args:
            event_urls: List of Facebook Event URLs to scrape
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not event_urls:
                logger.warning("No event URLs provided")
                return False
            
            # Prepare request data - just need the URLs
            data = [{"url": url} for url in event_urls]
            
            logger.info(f"Scraping {len(event_urls)} Facebook Events")
            
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