"""Configuration for event sources and their scrapers."""

from dataclasses import dataclass
from typing import Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Registry of available scrapers
SOURCES = {
    'peoply': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.peoply.PeoplyScraper'
    ),
    'navet': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.navet.NavetScraper'
    ),
    # TODO: Facebook scraper has different setup and should not be used like this
    'facebook': ScraperRegistration(
        enabled=False,
        scraper_class='src.scrapers.facebook.FacebookGroupScraper'
    )
}

def get_enabled_sources() -> Dict[str, ScraperRegistration]:
    """
    Get all enabled scrapers.
    
    Returns:
        Dict[str, ScraperRegistration]: Dictionary of source_id -> registration for all enabled scrapers
    """
    return {k: v for k, v in SOURCES.items() if v.enabled} 