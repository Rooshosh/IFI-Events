"""Configuration for event sources and their scrapers."""

from dataclasses import dataclass
from typing import Dict, Optional
import os

# Internal imports - environment must be first
from .environment import IS_PRODUCTION_ENVIRONMENT

@dataclass
class ScraperRegistration:
    """
    Registration of a scraper with the source manager.
    
    This class defines:
    1. Whether the scraper is currently enabled
    2. Where to find its implementation
    
    Fields:
        enabled: Whether this scraper is enabled
        scraper_class: Full path to scraper class (e.g., 'src.scrapers.peoply.PeoplyScraper')
    """
    enabled: bool
    scraper_class: str

# Registry of available scrapers for fetching new data
SOURCES = {
    'Peoply': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.peoply.PeoplyScraper'
    ),
    'Navet': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.navet.NavetScraper'
    ),
    'Facebook Post': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.facebook.FacebookGroupScraper'
    ),
    'Facebook Event': ScraperRegistration(
        enabled=False,
        scraper_class='src.scrapers.facebook_event.FacebookEventScraper'
    )
}

def get_enabled_sources() -> Dict[str, ScraperRegistration]:
    """
    Get all enabled scrapers.
    
    Returns:
        Dict[str, ScraperRegistration]: Dictionary of source_id -> registration for all enabled scrapers
    """
    return {k: v for k, v in SOURCES.items() if v.enabled}

def get_source_name_by_scraper(scraper_class: str) -> Optional[str]:
    """
    Get the source name for a given scraper class.
    
    Args:
        scraper_class: The full path to the scraper class (e.g., 'src.scrapers.peoply.PeoplyScraper')
        
    Returns:
        Optional[str]: The source name if found, None otherwise
    """
    for source_name, registration in SOURCES.items():
        if registration.scraper_class == scraper_class:
            return source_name
    return None 