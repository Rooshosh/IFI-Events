#!/usr/bin/env python3
"""Utility script to simulate webhook data by fetching from a previous BrightData snapshot."""

import os
import sys
import logging
import requests
import json
from pathlib import Path
import argparse

# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default snapshot ID (7 posts from 2025-03-02 to 2025-03-06)
DEFAULT_SNAPSHOT_ID = "s_m7xceqrg1y4ukprkuh"

def fetch_snapshot(snapshot_id: str) -> dict:
    """
    Fetch data from a previous BrightData snapshot.
    
    Args:
        snapshot_id: The ID of the snapshot to fetch
        
    Returns:
        dict: The snapshot data
    """
    api_key = os.getenv('BRIGHTDATA_API_KEY')
    if not api_key:
        raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
    
    url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    params = {
        "format": "json",
    }
    
    logger.info(f"Fetching snapshot {snapshot_id} from BrightData...")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    logger.info(f"Successfully fetched {len(data)} posts from snapshot")
    
    # Log the first post to see its structure
    if data:
        logger.info("First post structure:")
        logger.info(json.dumps(data[0], indent=2))
    
    return data

def format_data_for_webhook(data: list) -> dict:
    """
    Format the snapshot data to match the expected webhook format.
    
    Args:
        data: List of posts from the snapshot
        
    Returns:
        dict: Formatted data for the webhook
        
    The data format matches BrightData's Facebook Group Scraper output:
    {
        "posts": [
            {
                "url": "https://facebook.com/...",
                "post_id": "...",
                "user_username_raw": "Author Name",
                "content": "Post content",
                "date_posted": "2025-03-03T08:42:22.000Z",
                "num_comments": 0,
                "num_shares": 0,
                "num_likes_type": {"type": "Like", "num": 2},
                "group_name": "Group Name",
                "group_id": "...",
                // ... additional fields from BrightData
            },
            ...
        ]
    }
    """
    # The processor expects data in the format:
    # {
    #     "posts": [
    #         {
    #             "title": "Post title",
    #             "description": "Post content",
    #             "date": "2024-03-19T14:30:00",
    #             "url": "https://facebook.com/...",
    #             "author": "Post author"
    #         },
    #         ...
    #     ]
    # }
    formatted_data = {"posts": data}
    
    # Log the formatted data structure
    logger.info("Formatted webhook data structure:")
    logger.info(json.dumps(formatted_data, indent=2))
    
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
        
        # Get authorization header from environment
        auth_header = os.getenv('BRIGHTDATA_AUTHORIZATION_HEADER')
        if not auth_header:
            raise ValueError("BRIGHTDATA_AUTHORIZATION_HEADER environment variable is required for webhook authentication")

        # Send to webhook
        logger.info("Sending data to webhook...")
        response = requests.post(
            "http://localhost:8000/webhook/brightdata/facebook-group/results",
            json=webhook_data,
            headers={
                "Authorization": auth_header
            }
        )
        
        logger.info(f"Webhook response status: {response.status_code}")
        logger.info(f"Webhook response: {response.json()}")
        
    except Exception as e:
        logger.error(f"Error simulating webhook: {e}")
        raise

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Simulate webhook data by fetching from a BrightData snapshot')
    parser.add_argument('snapshot_id', nargs='?', default=DEFAULT_SNAPSHOT_ID,
                      help=f'Snapshot ID to fetch (default: {DEFAULT_SNAPSHOT_ID})')
    args = parser.parse_args()
    
    logger.info(f"Using snapshot ID: {args.snapshot_id}")
    simulate_webhook(args.snapshot_id) 