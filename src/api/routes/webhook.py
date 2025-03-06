"""Webhook endpoints for external notifications."""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import hmac
import hashlib
import os

router = APIRouter()

def verify_webhook_signature(request: Request, payload: bytes) -> bool:
    """Verify webhook signature from request."""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        return False
    
    # Get secret from environment
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        return False
    
    # Calculate expected signature
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

@router.post("")
async def handle_webhook(request: Request):
    """Handle incoming webhook notifications."""
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature
    if not verify_webhook_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")
    
    # TODO: Process webhook payload
    # This will be implemented based on the specific webhook requirements
    
    return {"status": "received"} 