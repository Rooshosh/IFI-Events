"""Scraper for ifinavet.no events"""

from datetime import datetime, timedelta
import logging
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import sys
from pathlib import Path

# Add src to Python path when running directly
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scrapers.base import BaseScraper
from src.models.event import Event
from src.utils.timezone import ensure_oslo_timezone, now_oslo

logger = logging.getLogger(__name__)

class NavetScraper(BaseScraper):
    """
    Scraper for ifinavet.no events.
    
    Fetches and parses events from Navet's event listing page and individual event pages.
    Handles both basic event information from the listing and detailed information
    from individual event pages.
    """
    
    # Default configuration
    BASE_URL = "https://ifinavet.no"
    DEFAULT_EVENT_DURATION = 2  # hours
    FETCH_DETAILS = False  # Whether to fetch individual event detail pages
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    def __init__(self):
        """Initialize the scraper with default settings"""
        self.base_url = self.BASE_URL
        self.headers = self.HEADERS.copy()
        self.fetch_details = self.FETCH_DETAILS
    
    def name(self) -> str:
        """Return the name of the scraper"""
        return "Navet"
    
    def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from a URL"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching HTML from {url}: {e}")
            raise
    
    def _parse_date_time(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into a datetime object"""
        try:
            # Extract day and month (format: "tirsdag 28.01")
            date_parts = date_str.strip().split()[-1].split('.')
            day = int(date_parts[0])
            month = int(date_parts[1])
            
            # Extract hours and minutes (format: "16:15")
            time_parts = time_str.strip().split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # Use current year as events are typically not more than a year in advance
            current_year = datetime.now().year
            naive_dt = datetime(current_year, month, day, hour, minute)
            return ensure_oslo_timezone(naive_dt)
            
        except Exception as e:
            logger.error(f"Error parsing date/time: {date_str} {time_str} - {str(e)}")
            raise
    
    def _get_event_url(self, onclick: str) -> str:
        """Extract event URL from onclick attribute"""
        url_path = onclick.split("'")[1]
        return urljoin(self.base_url, url_path)
    
    def _parse_event_details(self, event: Event, html: str) -> Event:
        """Parse additional event details from the event page"""
        if not event.source_url:
            return event
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            container = soup.find('div', class_='container')
            if not container:
                return event
            
            # Parse event details from the card
            card = container.find('div', class_='card')
            if card:
                # Update location and capacity
                for meta in card.find_all('div', class_='event-meta'):
                    icon = meta.find('span', class_=lambda x: x and x.startswith('icon-'))
                    value = meta.find('span', class_=None)
                    if not icon or not value:
                        continue
                    
                    icon_class = icon.get('class', [''])[0]
                    text = value.text.strip()
                    
                    if 'icon-location' in icon_class:
                        event.location = text
                    elif 'icon-users' in icon_class:
                        try:
                            event.spots_left = int(''.join(filter(str.isdigit, text)))
                        except ValueError:
                            pass
                
                # Update description with registration status
                status = card.find('h3', class_='event-status')
                if status:
                    event.description += f"\n\nPåmeldingsstatus: {status.text.strip()}"
                
                # Add detailed description
                description_parts = []
                h2 = card.find('h2')
                if h2:
                    description_parts.append(h2.text.strip())
                    for elem in h2.find_next_siblings(['p', 'ul']):
                        if elem.name == 'ul':
                            items = [f"- {li.text.strip()}" for li in elem.find_all('li')]
                            description_parts.append('\n'.join(items))
                        else:
                            description_parts.append(elem.text.strip())
                
                if description_parts:
                    event.description = '\n\n'.join(description_parts)
            
            # Add company information if available
            company_card = container.find('div', class_='company-card')
            if company_card:
                company_name = company_card.find('h2')
                company_desc = company_card.find('p')
                if company_name:
                    event.author = company_name.text.strip()
                    if company_desc:
                        event.description += f"\n\nOm {event.author}:\n{company_desc.text.strip()}"
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing details for event {event.title}: {e}")
            return event
    
    def _parse_event_card(self, event_item: BeautifulSoup) -> Optional[Event]:
        """Parse a single event card into an Event object"""
        try:
            # Get basic event information
            desc_container = event_item.find('div', class_='event-list-item-description')
            if not desc_container:
                return None
            
            # Get title
            title_link = desc_container.find('a')
            if not title_link:
                return None
            title = title_link.text.strip()
            
            # Get description
            desc_elem = desc_container.find('p')
            description = desc_elem.text.strip() if desc_elem else "Mer info kommer"
            
            # Get event metadata
            details = desc_container.find('div', class_='event-list-item-details')
            if not details:
                return None
            
            # Extract date, time and capacity
            meta = {
                'date': None,
                'time': None,
                'capacity': None
            }
            
            for item in details.find_all('div', class_='event-list-item-meta'):
                value = next((span for span in item.find_all('span') if not span.get('class')), None)
                if not value:
                    continue
                
                if 'icon-clock2' in str(item):
                    meta['time'] = value.text.strip()
                elif 'icon-calendar' in str(item):
                    meta['date'] = ' '.join(text.strip() for text in value.stripped_strings)
                elif 'icon-users' in str(item):
                    meta['capacity'] = value.text.strip()
            
            if not all([meta['date'], meta['time']]):
                return None
            
            # Parse start time and set end time
            start_time = self._parse_date_time(meta['date'], meta['time'])
            end_time = start_time + timedelta(hours=self.DEFAULT_EVENT_DURATION)
            
            # Get event URL
            onclick = event_item.get('onclick', '')
            source_url = self._get_event_url(onclick) if onclick else None
            
            # Create Event object
            return Event(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=None,  # Will be set from detailed page
                source_url=source_url,
                source_name=self.name(),
                fetched_at=now_oslo()
            )
        
        except Exception as e:
            logger.error(f"Error parsing event card: {e}")
            return None
    
    def get_events(self) -> List[Event]:
        """Get events from ifinavet.no"""
        try:
            # Fetch main page
            url = f"{self.base_url}/arrangementer/2025/var/"
            html = self._fetch_html(url)
            
            # Find event cards
            soup = BeautifulSoup(html, 'html.parser')
            container = soup.find('div', class_='event-list-container')
            if not container:
                logger.error("Could not find event list container")
                return []
            
            event_cards = container.find_all('div', class_='event-list-item-wrapper', recursive=True)
            logger.info(f"Found {len(event_cards)} event cards")
            
            # Parse events
            events = []
            for card in event_cards:
                event = self._parse_event_card(card)
                if event:
                    # Only fetch details if enabled
                    if self.fetch_details:
                        details_html = self._fetch_html(event.source_url)
                        event = self._parse_event_details(event, details_html)
                    events.append(event)
            
            logger.info(f"Successfully parsed {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events from {self.name()}: {e}")
            return []

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run scraper
    scraper = NavetScraper()
    events = scraper.get_events()
    
    # Print results
    print(f"\nFound {len(events)} events:")
    for event in events:
        print(f"\nTitle: {event.title}")
        print(f"Date: {event.start_time}")
        print(f"Location: {event.location}")
        print(f"URL: {event.source_url}")
        if event.author:
            print(f"Organizer: {event.author}")
        print("-" * 40) 