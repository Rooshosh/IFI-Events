"""Admin router module."""

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
import os
import subprocess
from pathlib import Path

router = APIRouter(tags=["admin"])

async def run_fetch_script():
    """Background task to run the fetch script."""
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

@router.post("/admin/fetch")
async def trigger_fetch(
    background_tasks: BackgroundTasks,
    authorization: str = Header(...)
):
    """
    Trigger a fetch of new events.
    This endpoint is protected by an authorization header.
    """
    # Check authorization
    if authorization != os.environ.get('ADMIN_API_KEY'):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization"
        )
    
    # Add fetch task to background tasks
    background_tasks.add_task(run_fetch_script)
    
    return {
        "status": "success",
        "message": "Fetch task started"
    } 