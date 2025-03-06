import requests
import json
from datetime import datetime

def test_api():
    base_url = "http://localhost:8000"
    
    # Test root endpoint
    print("\nTesting root endpoint...")
    response = requests.get(f"{base_url}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test events endpoint
    print("\nTesting events endpoint...")
    response = requests.get(f"{base_url}/events")
    print(f"Status: {response.status_code}")
    events = response.json()
    print(f"Number of events found: {len(events)}")
    if events:
        print("\nFirst event details:")
        print(json.dumps(events[0], indent=2, default=str))
    
    # Test single event endpoint (if we have events)
    if events:
        event_id = events[0]['id']
        print(f"\nTesting single event endpoint for event {event_id}...")
        response = requests.get(f"{base_url}/events/{event_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
    
    # Test non-existent event
    print("\nTesting non-existent event...")
    response = requests.get(f"{base_url}/events/999999")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_api() 