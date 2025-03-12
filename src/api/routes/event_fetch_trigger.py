"""Routes for triggering event fetches from external sources."""

import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks

router = APIRouter(prefix="/admin", tags=["admin"])

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
    if authorization != os.environ.get('CUSTOM_ADMIN_API_KEY'):
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