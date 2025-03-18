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
    3. Priority of the source (higher number = higher priority)
    
    Fields:
        enabled: Whether this scraper is enabled
        scraper_class: Full path to scraper class (e.g., 'src.scrapers.peoply.PeoplyScraper')
        priority: Priority of this source (higher number = higher priority)
    """
    enabled: bool
    scraper_class: str
    priority: int

# Registry of available scrapers for fetching new data
SOURCES = {
    'Peoply': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.peoply.PeoplyScraper',
        priority=100
    ),
    'Navet': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.navet.NavetScraper',
        priority=90
    ),
    'Facebook Post': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.facebook.FacebookGroupScraper',
        priority=10
    ),
    'Facebook Event': ScraperRegistration(
        enabled=False,
        scraper_class='src.scrapers.facebook_event.FacebookEventScraper',
        priority=70
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

def compare_source_priorities(source1: str, source2: str) -> int:
    """
    Compare the priorities of two sources.
    
    Args:
        source1: Name of first source
        source2: Name of second source
        
    Returns:
        int: 1 if source1 has higher priority, -1 if source2 has higher priority, 0 if equal
    """
    priority1 = SOURCES.get(source1, ScraperRegistration(enabled=False, scraper_class='', priority=0)).priority
    priority2 = SOURCES.get(source2, ScraperRegistration(enabled=False, scraper_class='', priority=0)).priority
    return 1 if priority1 > priority2 else (-1 if priority1 < priority2 else 0) 