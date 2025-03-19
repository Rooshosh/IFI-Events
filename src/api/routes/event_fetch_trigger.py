"""Routes for triggering event fetches from external sources."""

import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from dataclasses import dataclass

router = APIRouter(prefix="/admin", tags=["admin"])

@dataclass
class AdminConfig:
    """Admin configuration settings."""
    
    api_key: str = ""
    
    def __post_init__(self):
        """Load API key from environment if not provided."""
        if not self.api_key:
            self.api_key = os.environ.get('CUSTOM_ADMIN_API_KEY', '')
    
    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.api_key:
            raise ValueError("CUSTOM_ADMIN_API_KEY environment variable is required")
        return True
    
    def verify_auth(self, auth_header: str) -> bool:
        """Verify admin authorization header."""
        return bool(auth_header and auth_header == self.api_key)

async def execute_fetch_script():
    """Execute the script that fetches events from all sources."""
    try:
        script_path = Path(__file__).parent.parent.parent.parent / 'scripts' / 'get_new_data.py'
        # Run the script with a timeout to prevent hanging
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Script failed with error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Script timed out after 5 minutes")
    except Exception as e:
        raise Exception(f"Failed to run fetch script: {str(e)}")

@router.post("/trigger-fetch")
async def trigger_event_fetch(
    background_tasks: BackgroundTasks,
    authorization: str = Header(...)
):
    """
    Trigger a fetch of events from all external sources.
    This endpoint is protected by an authorization header.
    """
    # Check authorization
    admin_config = AdminConfig()
    admin_config.validate()
    
    if not admin_config.verify_auth(authorization):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization"
        )
    
    # Add fetch task to background tasks
    background_tasks.add_task(execute_fetch_script)
    
    return {
        "status": "success",
        "message": "Event fetch triggered successfully"
    } 