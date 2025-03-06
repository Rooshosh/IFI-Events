"""Webhook routes module."""

from fastapi import APIRouter
from src.webhooks.handlers.brightdata_facebook_group import router as brightdata_facebook_group_router

# Create the main webhook router
router = APIRouter()

# Include the BrightData Facebook Group handler
router.include_router(brightdata_facebook_group_router) 