"""Base interface that all event scrapers must implement."""

from typing import List
from abc import ABC, abstractmethod
from ..models.event import Event

class BaseScraper(ABC):
    """
    Base interface for all event scrapers.
    
    Each scraper is responsible for:
    1. Fetching events from a specific source (e.g., peoply.app, ifinavet.no)
    2. Converting the source's event format into our Event model
    3. Handling its own configuration and authentication if needed
    
    Required Methods:
        name(): Returns the scraper's identifier (e.g., 'peoply.app')
        get_events(): Fetches and returns a list of events from the source
    """
    
    @abstractmethod
    def name(self) -> str:
        """
        Return the name/identifier of this scraper.
        This should match the name in the source configuration.
        
        Returns:
            str: The scraper's identifier (e.g., 'peoply.app', 'ifinavet.no')
        """
        pass
    
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