"""Scraper for Facebook group posts using BrightData's API."""

from datetime import datetime, timedelta
import logging
import time
from typing import List, Optional, Dict, Any
import requests
import json
from .base import BaseScraper
from ..models.event import Event
from ..utils.timezone import now_oslo, ensure_oslo_timezone
from ..config.sources import SOURCES
from ..utils.llm import init_openai, is_event_post, parse_event_details
from ..db import get_db
from sqlalchemy import func

logger = logging.getLogger(__name__)

class FacebookGroupScraper(BaseScraper):
    """
    Scraper for Facebook group posts using BrightData's API.
    
    This scraper uses BrightData's 'Facebook - Posts by group URL' dataset
    to fetch posts from the IFI Students Facebook group, then uses an LLM
    to identify and parse events from these posts.
    """
    
    def __init__(self):
        # Get configuration from sources
        config = SOURCES['facebook']
        brightdata_config = config.settings['brightdata']
        openai_config = config.settings['openai']
        
        self.base_url = config.base_url
        self.headers = {
            "Authorization": f"Bearer {brightdata_config['api_key']}",
            "Content-Type": "application/json",
        }
        self.params = {
            "dataset_id": brightdata_config['dataset_id'],
            "include_errors": "true",
        }
        self.group_url = brightdata_config['group_url']
        self.days_to_fetch = brightdata_config.get('days_to_fetch', 1)  # Default to 1 if not specified
        
        self.max_poll_attempts = 60  # Up to 1 hour total (60 attempts)
        self.poll_interval = 60  # seconds (1 minute)
        self.initial_wait = 90  # seconds
        
        # Initialize OpenAI client
        init_openai(openai_config['api_key'])
        self.openai_config = openai_config
    
    def name(self) -> str:
        """Return the name of the scraper."""
        return SOURCES['facebook'].name
    
    def _extract_post_id(self, url: str) -> Optional[str]:
        """Extract the post ID from a Facebook post URL."""
        if not url:
            return None
        try:
            return url.split('/posts/')[-1].strip('/')
        except Exception:
            logger.warning(f"Could not extract post ID from URL: {url}")
            return None

    def _get_event_urls_for_timeframe(self, num_days: int = 1) -> List[str]:
        """
        Get source URLs of events from the last N days.
        
        Args:
            num_days: Number of days to look back (default: 1 for today only)
        """
        db = get_db()
        try:
            # Get date range in Oslo timezone
            end_date = now_oslo().date()
            start_date = end_date - timedelta(days=num_days - 1)
            
            # Query for events in date range
            events = db.query(Event).filter(
                Event.source_name == self.name(),
                Event.created_at >= start_date
            ).all()
            
            return [event.source_url for event in events if event.source_url]
        finally:
            db.close()

    def _trigger_scrape(self) -> Optional[str]:
        """
        Trigger a new scrape of the Facebook group.
        
        Returns:
            snapshot_id if successful, None otherwise.
        """
        try:
            # Get existing event URLs to avoid re-scraping
            existing_urls = self._get_event_urls_for_timeframe(self.days_to_fetch)
            logger.info(f"Found {len(existing_urls)} existing events in the last {self.days_to_fetch} days")
            
            # Prepare request data
            data = {
                "url": self.group_url,
                "posts_limit": 50,  # Fetch up to 50 posts
                "days_limit": self.days_to_fetch,  # Only fetch posts from last N days
            }
            
            # Make the request
            response = requests.post(
                f"{self.base_url}/trigger",
                headers=self.headers,
                params=self.params,
                json=data
            )
            response.raise_for_status()
            
            # Extract snapshot ID from response
            snapshot_id = response.text.strip()
            logger.info(f"Successfully triggered scrape with snapshot ID: {snapshot_id}")
            return snapshot_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Other error: {str(e)}")
            return None
    
    def _check_status(self, snapshot_id: str) -> bool:
        """
        Check the status of a scrape.
        Returns True if complete, False otherwise.
        """
        try:
            response = requests.get(
                f"{self.base_url}/progress/{snapshot_id}",
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Log the current status
            logger.debug(f"Scrape status for {snapshot_id}: {result}")
            
            # Check status field in response
            if isinstance(result, dict) and 'status' in result:
                status = result['status']
                logger.info(f"Current status: {status}")
                return status == "ready"
            
            # Fallback for old format
            return result == "ready"
            
        except Exception as e:
            logger.error(f"Error checking status for snapshot {snapshot_id}: {e}")
            return False
    
    def _fetch_posts_from_snapshot(self, snapshot_id: str) -> str:
        """
        Fetch posts directly from an existing snapshot ID.
        This is useful when we know a scrape has already completed.
        """
        try:
            response = requests.get(
                f"{self.base_url}/snapshot/{snapshot_id}",
                headers=self.headers,
                params={"format": "json"}
            )
            
            # Debug logging for request
            logger.info(f"Fetching snapshot with:")
            logger.info(f"URL: {self.base_url}/snapshot/{snapshot_id}")
            logger.info(f"Headers: {self.headers}")
            logger.info(f"Params: {{'format': 'json'}}")
            
            # Handle empty snapshots (returns 400 with "Snapshot is empty" message)
            if response.status_code == 400 and response.text.strip() == "Snapshot is empty":
                logger.info(f"Snapshot {snapshot_id} is empty, returning empty list")
                return json.dumps([])
            
            # For all other responses, check status code
            response.raise_for_status()
            results = response.json()
            
            logger.info(f"Successfully retrieved {len(results)} posts from snapshot {snapshot_id}")
            return json.dumps(results)
            
        except Exception as e:
            logger.error(f"Error retrieving results for snapshot {snapshot_id}: {e}")
            raise
    
    def _fetch_posts(self, url: str = None, snapshot_id: str = None) -> str:
        """
        Fetch posts from the Facebook group.
        
        Args:
            url: Dummy parameter to satisfy the cached_request decorator.
                 Not actually used since we're using cache_key.
            snapshot_id: Optional snapshot ID to fetch from directly.
                        If provided, skips triggering a new scrape.
        """
        # If snapshot_id is provided, fetch directly from it
        if snapshot_id:
            return self._fetch_posts_from_snapshot(snapshot_id)
            
        # Otherwise, do the normal scrape process
        url = url or f"{self.base_url}/trigger"
        
        # Trigger new scrape
        snapshot_id = self._trigger_scrape()
        if not snapshot_id:
            raise Exception("Failed to trigger scrape")
        
        logger.info(f"Waiting initial {self.initial_wait} seconds for scrape to complete...")
        time.sleep(self.initial_wait)
        
        # Poll for completion
        attempts = 0
        while attempts < self.max_poll_attempts:
            if self._check_status(snapshot_id):
                # Get the results
                return self._fetch_posts_from_snapshot(snapshot_id)
            
            logger.info(f"Still waiting... (attempt {attempts + 1}/{self.max_poll_attempts})")
            time.sleep(self.poll_interval)
            attempts += 1
        
        raise Exception("Scrape timed out or failed to retrieve results")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure scraper settings from dictionary."""
        if config is None:
            return
            
        # Update configurable parameters
        if 'days_to_fetch' in config:
            self.days_to_fetch = config['days_to_fetch']
        if 'initial_wait' in config:
            self.initial_wait = config['initial_wait']
        if 'poll_interval' in config:
            self.poll_interval = config['poll_interval']
        if 'max_attempts' in config:
            self.max_poll_attempts = config['max_attempts']
    
    def get_events(self, snapshot_id: str = None) -> List[Event]:
        """
        Get events from Facebook group posts.
        
        Args:
            snapshot_id: Optional snapshot ID to fetch from directly
        """
        try:
            logger.info(f"Fetching Facebook posts for the last {self.days_to_fetch} days")
            # Fetch posts
            posts_json = self._fetch_posts(
                url=self.base_url + "/trigger",
                snapshot_id=snapshot_id
            )
            posts = json.loads(posts_json)
            
            # Filter out "no results" records (they have url=null and usually a warning message)
            valid_posts = [post for post in posts if post.get('url') is not None]
            if len(valid_posts) < len(posts):
                logger.info(f"Filtered out {len(posts) - len(valid_posts)} 'no results' records")
                if not valid_posts:
                    logger.info("No valid posts found in response")
                    return []
            
            # Find the date range of the fetched posts
            post_dates = []
            for post in valid_posts:
                try:
                    if post.get('date_posted'):
                        post_date = ensure_oslo_timezone(datetime.fromisoformat(post['date_posted'])).date()
                        post_dates.append(post_date)
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date_posted: {post.get('date_posted')}")
                    continue
            
            if not post_dates:
                logger.warning("No valid dates found in posts")
                return []
            
            # Get the date range
            start_date = min(post_dates)
            end_date = max(post_dates)
            logger.info(f"Posts span from {start_date} to {end_date}")
            
            # Get URLs of events we already have in the database for this date range
            db = get_db()
            try:
                existing_events = db.query(Event).filter(
                    Event.source_name == self.name(),
                    Event.start_time >= start_date,
                    Event.start_time <= end_date + timedelta(days=1)
                ).all()
                existing_urls = {event.source_url for event in existing_events if event.source_url}
                logger.info(f"Found {len(existing_urls)} existing events in date range")
            finally:
                db.close()
            
            # Process each post
            events = []
            for post in valid_posts:
                try:
                    # Skip if we already have this event
                    post_url = post.get('url')
                    if post_url in existing_urls:
                        logger.debug(f"Skipping already processed post: {post_url}")
                        continue
                    
                    # Check if this is an event post
                    if not is_event_post(post.get('text', '')):
                        logger.debug(f"Post is not an event: {post_url}")
                        continue
                    
                    # Parse event details
                    event_details = parse_event_details(post.get('text', ''))
                    if not event_details:
                        logger.warning(f"Failed to parse event details from post: {post_url}")
                        continue
                    
                    # Create event object
                    event = Event(
                        title=event_details.get('title', 'Untitled Event'),
                        description=event_details.get('description', ''),
                        start_time=event_details.get('start_time'),
                        end_time=event_details.get('end_time'),
                        location=event_details.get('location'),
                        source_url=post_url,
                        source_name=self.name(),
                        fetched_at=now_oslo()
                    )
                    
                    # Add to list if we have required fields
                    if event.title and event.start_time:
                        events.append(event)
                    else:
                        logger.warning(f"Skipping event with missing required fields: {post_url}")
                
                except Exception as e:
                    logger.error(f"Error processing post: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(events)} events from {len(valid_posts)} posts")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events from Facebook: {e}")
            return [] 