"""Scraper for peoply.app events"""

from datetime import datetime
from typing import List
import requests
import logging
import json

from src.scrapers.base import SyncScraper
from src.models.event import Event
from zoneinfo import ZoneInfo
from src.utils.timezone import now_oslo

logger = logging.getLogger(__name__)

class PeoplyScraper(SyncScraper):
    """Scraper for peoply.app events"""
    
    # Default configuration
    BASE_URL = "https://api.peoply.app"
    EVENTS_LIMIT = 99
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    def __init__(self):
        """Initialize the scraper with default settings"""
        self.base_url = self.BASE_URL
        self.headers = self.HEADERS.copy()
        self.events_limit = self.EVENTS_LIMIT
    
    def name(self) -> str:
        """Return the name of the scraper"""
        return "Peoply"
    
    def _get_api_url(self) -> str:
        """Generate the URL for peoply.app events API with the current date"""
        # Convert Oslo time to UTC for the API
        current_time = now_oslo().astimezone(ZoneInfo("UTC"))
        time_str = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        encoded_time = time_str.replace(':', '%3A')
        return f"{self.base_url}/events?afterDate={encoded_time}&orderBy=startDate&take={self.events_limit}"
    
    def _fetch_json(self, url: str) -> str:
        """Fetch JSON content"""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        # Parse and re-format JSON to make it readable
        data = response.json()
        return json.dumps(data, indent=2, ensure_ascii=False)  # ensure_ascii=False preserves unicode characters
    
    def get_events(self) -> List[Event]:
        """Get events from peoply.app API"""
        try:
            # Fetch events from API
            api_url = self._get_api_url()
            raw_response = self._fetch_json(api_url)
            
            api_events = json.loads(raw_response)
            logger.info(f"Found {len(api_events)} events from API")
            
            events = []
            for api_event in api_events:
                try:
                    # Convert API event to our format
                    event = Event(
                        title=api_event['title'],
                        description=api_event['description'],
                        start_time=datetime.fromisoformat(api_event['startDate'].replace('Z', '+00:00')),
                        end_time=(
                            datetime.fromisoformat(api_event['endDate'].replace('Z', '+00:00'))
                            if api_event.get('endDate')
                            else None
                        ),
                        location=api_event['locationName'],
                        source_url=f"https://peoply.app/events/{api_event['urlId']}",
                        source_name=self.name(),
                        fetched_at=now_oslo()
                    )
                    
                    # Add additional location details if available
                    if api_event.get('freeformAddress'):
                        event.location = f"{api_event['locationName']}, {api_event['freeformAddress']}"
                    
                    # Add categories to description
                    categories = [cat['category']['name'] for cat in api_event.get('eventCategories', [])]
                    if categories:
                        event.description = f"{event.description}\n\nCategories: {', '.join(categories)}"
                    
                    # Set the author to the organization name
                    for arranger in api_event.get('eventArrangers', []):
                        if arranger.get('role') == 'ADMIN':
                            if arranger['arranger'].get('organization'):
                                event.author = arranger['arranger']['organization']['name']
                            elif arranger['arranger'].get('user'):
                                user = arranger['arranger']['user']
                                event.author = f"{user['firstName']} {user['lastName']}"
                            break
                    
                    events.append(event)
                    logger.info(f"Successfully parsed event: {event.title} ({event.start_time} - {event.end_time})")
                
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    continue
            
            return events

        except Exception as e:
            logger.error(f"Error fetching events from {self.name()}: {e}")
            return []

