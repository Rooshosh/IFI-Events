"""Base interface that all event scrapers must implement."""

from typing import List, Optional
from abc import ABC, abstractmethod
from ..models.event import Event
from ..config.data_sources import get_source_display_name

class BaseScraper(ABC):
    """
    Base interface for all event scrapers.
    
    Each scraper is responsible for:
    1. Fetching events from a specific source (e.g., peoply.app, ifinavet.no)
    2. Converting the source's event format into our Event model
    3. Handling its own configuration and authentication if needed
    """
    
    def __init__(self, source_id: str):
        """
        Initialize the scraper with its source ID.
        
        Args:
            source_id: The source identifier (e.g., 'facebook-post')
        """
        self.source_id = source_id

    def name(self) -> str:
        """
        Return the display name of this scraper from the configuration.
        
        Returns:
            str: The scraper's display name (e.g., 'Facebook Post')
            
        Raises:
            ValueError: If no display name is found for this source ID
        """
        display_name = get_source_display_name(self.source_id)
        if not display_name:
            raise ValueError(f"No display name found for source ID: {self.source_id}")
        return display_name

class SyncScraper(BaseScraper):
    """
    Base class for synchronous scrapers that directly return events.
    
    This is for scrapers that can immediately fetch and return events,
    like peoply.app and ifinavet.no.
    
    Required Methods:
        get_events(): Fetches and returns a list of events from the source
    """
    
    @abstractmethod
    def get_events(self) -> List[Event]:
        """
        Fetch and return events from this source.
        
        This method should:
        1. Fetch data from the source (e.g., API call, web scraping)
        2. Parse the data into Event objects
        3. Handle any errors gracefully
        
        Returns:
            List[Event]: List of events from this source
        """
        pass

class AsyncScraper(BaseScraper):
    """
    Base class for asynchronous scrapers that trigger data fetching.
    
    This is for scrapers that need to trigger a data fetch operation
    that will be handled later by a webhook or callback, like the Facebook scraper.
    
    Required Methods:
        initialize_data_fetch(): Triggers the data fetching process
    """
    
    @abstractmethod
    def initialize_data_fetch(self) -> bool:
        """
        Initialize the data fetching process.
        
        This method should:
        1. Trigger the data fetching process (e.g., API call, webhook setup)
        2. Handle any errors gracefully
        
        Returns:
            bool: True if the fetch was successfully initiated, False otherwise
        """
        pass 