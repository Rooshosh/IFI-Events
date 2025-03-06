#!/usr/bin/env python3
"""Utility script to simulate webhook data by fetching from a previous BrightData snapshot."""

import os
import sys
import logging
import requests
from pathlib import Path

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
    return data

def simulate_webhook(snapshot_id: str):
    """
    Simulate webhook data by fetching from a snapshot and sending it to our webhook.
    
    Args:
        snapshot_id: The ID of the snapshot to fetch
    """
    try:
        # Fetch data from snapshot
        data = fetch_snapshot(snapshot_id)
        
        # Get authorization header from environment
        auth_header = os.getenv('BRIGHTDATA_AUTHORIZATION_HEADER')
        if not auth_header:
            raise ValueError("BRIGHTDATA_AUTHORIZATION_HEADER environment variable is required for webhook authentication")

        # Send to webhook
        logger.info("Sending data to webhook...")
        response = requests.post(
            # TODO: only works on localhost
            "http://localhost:8000/webhook/brightdata/results",
            json=data,
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
    # Use provided snapshot ID or default
    snapshot_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SNAPSHOT_ID
    logger.info(f"Using snapshot ID: {snapshot_id}")
    simulate_webhook(snapshot_id) 