#!/usr/bin/env python3
"""Utility script to simulate webhook data for Facebook Events by fetching from a previous BrightData snapshot."""

import os
import sys
import logging
import requests
import json
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DEFAULT_SNAPSHOT_ID = "s_m8dd8tjd2cdyc0ffeh" # 11 events 
# DEFAULT_SNAPSHOT_ID = "s_m8diu1qp1nqaku1jbd" # 9 events fetched at March 17. 9PM
DEFAULT_SNAPSHOT_ID = "s_m8fv7yphdl4vkduaa"

def fetch_snapshot(snapshot_id: str) -> dict:
    """
    Fetch data from a previous BrightData snapshot.
    
    Args:
        snapshot_id: The ID of the snapshot to fetch
        
    Returns:
        dict: The snapshot data
    """
    config = get_brightdata_config()
    
    url = f"{config['base_url']}/snapshot/{snapshot_id}"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": config['content_type'],
    }
    params = {
        "format": "json",
    }
    
    logger.info(f"Fetching snapshot {snapshot_id} from BrightData...")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    logger.info(f"Successfully fetched {len(data)} events from snapshot")
    
    # Log each event's basic info
    for event in data:
        username = event.get('event_by', [{}])[0].get('name', 'Unknown')
        url = event.get('url', 'No URL')
        logger.info(f"Username: {username} - Event-url: {url}")
    
    return data

def format_data_for_webhook(data: list) -> dict:
    """
    Format the snapshot data to match the expected webhook format for Facebook Events.
    
    Args:
        data: List of events from the snapshot
        
    Returns:
        dict: Formatted data for the webhook
    """
    # The processor expects data in the format:
    # {
    #     "events": [
    #         {
    #             "title": "Event title",
    #             "description": "Event description",
    #             "start_date": "2024-03-19T14:30:00",
    #             "end_date": "2024-03-19T16:30:00",
    #             "location": "Event location",
    #             "url": "https://facebook.com/events/...",
    #             "organizer": "Event organizer"
    #         },
    #         ...
    #     ]
    # }
    formatted_data = {"events": data}
    return formatted_data

def simulate_webhook(snapshot_id: str):
    """
    Simulate webhook data by fetching from a snapshot and sending it to our webhook.
    
    Args:
        snapshot_id: The ID of the snapshot to fetch
    """
    try:
        # Fetch data from snapshot
        raw_data = fetch_snapshot(snapshot_id)
        
        # Format data for webhook
        webhook_data = format_data_for_webhook(raw_data)
        
        # Get configuration
        config = get_brightdata_config()

        # Send to webhook
        logger.info("Sending data to webhook...")
        response = requests.post(
            "http://localhost:8000/webhook/brightdata/facebook-events/results",
            json=webhook_data,
            headers={
                "Authorization": config['webhook_auth']
            }
        )
        
        logger.info(f"Webhook response status: {response.status_code}")
        logger.info(f"Webhook response: {response.json()}")
        
    except Exception as e:
        logger.error(f"Error simulating webhook: {e}")
        raise

if __name__ == "__main__":
    # Add project root to Python path only when running directly
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))
    
    # Import after setting up Python path
    from src.config.external_services.brightdata import get_brightdata_config
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Simulate webhook data for Facebook Events by fetching from a BrightData snapshot')
    parser.add_argument('snapshot_id', nargs='?', default=DEFAULT_SNAPSHOT_ID,
                      help=f'Snapshot ID to fetch (default: {DEFAULT_SNAPSHOT_ID})')
    args = parser.parse_args()
    
    logger.info(f"Using snapshot ID: {args.snapshot_id}")
    simulate_webhook(args.snapshot_id) 