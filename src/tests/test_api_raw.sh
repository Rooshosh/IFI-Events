#!/bin/bash

# Test health endpoint
echo "Testing health endpoint..."
curl -v https://ifi-events-data-service.up.railway.app/health

echo -e "\n\nTesting events endpoint..."
curl -v https://ifi-events-data-service.up.railway.app/api/events 