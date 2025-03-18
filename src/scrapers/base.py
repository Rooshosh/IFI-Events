"""Base interface that all event scrapers must implement."""

from typing import List, Optional
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

    def get_source_name(self) -> Optional[str]:
        """
        Get the source name for this scraper from the data sources configuration.
        
        Returns:
            Optional[str]: The source name if found in configuration, None otherwise
        """
        from src.config.data_sources import get_source_name_by_scraper
        return get_source_name_by_scraper(self.__class__.__module__ + '.' + self.__class__.__name__)

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