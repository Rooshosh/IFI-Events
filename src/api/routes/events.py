"""API routes for event management."""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ...db.base import get_db
from ...services.scrape_service import ScrapeService
from ...models.scrape_job import JobStatus

router = APIRouter()

async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify API key from header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key missing")
    # TODO: Add proper API key verification
    return x_api_key

@router.post("/fetch")
async def fetch_events(
    source: str = "all",
    live: bool = False,
    no_store: bool = False,
    detailed: bool = False,
    quiet: bool = False,
    snapshot_id: Optional[str] = None,
    debug: bool = False,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Start an asynchronous event fetch operation."""
    service = ScrapeService(db)
    
    if source == "facebook":
        # Start Facebook scraping job
        job = service.initiate_facebook_scrape({
            'live': live,
            'no_store': no_store,
            'detailed': detailed,
            'quiet': quiet,
            'snapshot_id': snapshot_id,
            'debug': debug
        })
        return {
            'job_id': job.id,
            'status': job.status.value,
            'message': 'Facebook scraping job initiated'
        }
    else:
        # For other sources, process immediately
        # TODO: Implement immediate processing for other sources
        raise HTTPException(status_code=501, detail="Not implemented for this source")

@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get the status of a scraping job."""
    service = ScrapeService(db)
    job = service.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = {
        'job_id': job.id,
        'status': job.status.value,
        'source': job.source,
        'created_at': job.created_at.isoformat(),
        'updated_at': job.updated_at.isoformat() if job.updated_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'error_message': job.error_message
    }
    
    if job.status == JobStatus.COMPLETED:
        response['result'] = job.result
    
    return response

@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """List all scraping jobs."""
    service = ScrapeService(db)
    jobs = service.list_jobs(status, source)
    
    return {
        'jobs': [{
            'job_id': job.id,
            'status': job.status.value,
            'source': job.source,
            'created_at': job.created_at.isoformat(),
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message
        } for job in jobs]
    } 