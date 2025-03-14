"""Helper script to run any of the available scrapers interactively.

This script provides a command-line interface to run any of the available scrapers:
- Facebook Group Scraper: Triggers a remote scrape via BrightData. Results will be sent to a webhook.
  Note: The --no-store flag has no effect for this scraper as storage is handled by the webhook.
- Navet Scraper: Scrapes events from ifinavet.no
  Note: Supports --no-details flag to skip fetching detailed information for each event.
- Peoply Scraper: Scrapes events from peoply.app

The script will prompt the user to select which scraper to run and handle the execution.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add src to Python path when running directly
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scrapers.facebook import FacebookGroupScraper
from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.new_event_handler import process_new_events

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_facebook_scraper(store_in_db: bool = True, fetch_details: bool = True):
    """Run the Facebook Group scraper."""
    if not store_in_db:
        raise ValueError(
            "The --no-store flag cannot be used with the Facebook scraper. "
            "This scraper triggers a remote scrape via BrightData, and storage "
            "is handled by the webhook."
        )
    
    if not fetch_details:
        raise ValueError(
            "The --no-details flag cannot be used with the Facebook scraper. "
            "This scraper triggers a remote scrape via BrightData and does not "
            "support detailed fetching."
        )
    
    scraper = FacebookGroupScraper()
    success = scraper.initialize_data_fetch()
    
    if success:
        print("\nScrape triggered successfully!")
        print("Results will be sent to the configured webhook.")
    else:
        print("\nFailed to trigger scrape.")
        print("Check the logs for more details.")

def run_navet_scraper(store_in_db: bool = True, fetch_details: bool = True):
    """Run the Navet scraper."""
    scraper = NavetScraper()
    scraper.fetch_details = fetch_details
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
    
    # Store events if enabled
    if store_in_db and events:
        new_count, updated_count = process_new_events(events, scraper.name())
        print(f"\nStored events: {new_count} new, {updated_count} updated")

def run_peoply_scraper(store_in_db: bool = True, fetch_details: bool = True):
    """Run the Peoply scraper."""
    if not fetch_details:
        raise ValueError(
            "The --no-details flag cannot be used with the Peoply scraper. "
            "This scraper fetches all event details from the API and does not "
            "support skipping detailed information."
        )
    
    scraper = PeoplyScraper()
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
    
    # Store events if enabled
    if store_in_db and events:
        new_count, updated_count = process_new_events(events, scraper.name())
        print(f"\nStored events: {new_count} new, {updated_count} updated")

def main():
    """Main function to handle scraper selection and execution."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run any of the available scrapers')
    parser.add_argument('--no-store', action='store_true', help='Do not store events in database (not supported for Facebook scraper)')
    parser.add_argument('--no-details', action='store_true', help='Do not fetch detailed information (only supported for Navet scraper)')
    args = parser.parse_args()
    
    # Default value for storing events in database
    store_in_db = not args.no_store
    
    # Available scrapers
    scrapers = {
        '1': ('Facebook Group Scraper', lambda: run_facebook_scraper(store_in_db, not args.no_details)),
        '2': ('Navet Scraper', lambda: run_navet_scraper(store_in_db, not args.no_details)),
        '3': ('Peoply Scraper', lambda: run_peoply_scraper(store_in_db, not args.no_details))
    }
    
    # Print menu
    print("\nAvailable scrapers:")
    for key, (name, _) in scrapers.items():
        print(f"{key}. {name}")
    
    # Get user input
    while True:
        choice = input("\nSelect a scraper to run (1-3) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("Exiting...")
            break
            
        if choice in scrapers:
            name, func = scrapers[choice]
            print(f"\nRunning {name}...")
            try:
                func()
            except ValueError as e:
                print(f"\nError: {str(e)}")
                print("Please try again with different options.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 