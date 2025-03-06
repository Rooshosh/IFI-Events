"""Webhook handlers for various event sources.

This module provides a centralized router for all webhook endpoints.
To add a new webhook endpoint:

1. Create a new handler file in src/webhooks/handlers/:
   ```python
   # src/webhooks/handlers/new_source.py
   from fastapi import APIRouter
   
   # Create router without prefix (it's handled by the main webhook router)
   router = APIRouter(tags=["new_source"])
   
   @router.post("/new_source/results")
   async def handle_new_source_webhook():
       # Your webhook handling logic here
       pass
   ```

2. Add the new router to this file:
   ```python
   from .handlers.new_source import router as new_source_router
   router.include_router(new_source_router)
   ```

The new webhook will be available at /webhook/new_source/results
"""

from fastapi import APIRouter

# Create the main webhook router with the /webhook prefix
router = APIRouter(prefix="/webhook", tags=["webhooks"])

# Import and include all webhook handlers
from .handlers.brightdata_facebook_group import router as brightdata_facebook_group_router
router.include_router(brightdata_facebook_group_router)

# Export the main webhook router
__all__ = ['router'] 