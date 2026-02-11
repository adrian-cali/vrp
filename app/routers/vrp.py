from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.database import get_db
from app.schemas import VRPJobCreate, VRPJobResponse, VRPJobDetail, VRPJobSummary, VRPJobListResponse
from app.services.db_service import db_service

router = APIRouter(prefix="/api/v1/vrp", tags=["VRP"])


@router.post("/plan-ahead", response_model=VRPJobResponse)
async def plan_ahead(
    job_create: VRPJobCreate,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Convenience endpoint for creating VRP job
    """
    user_id = UUID(x_user_id) if x_user_id else UUID("24e7d141-6d7c-4e9b-992e-89c944f92ad6")
    return await create_vrp_job(job_create, user_id, db)


@router.post("/jobs", response_model=VRPJobResponse)
async def create_vrp_job(
    job_create: VRPJobCreate,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user_id = UUID(x_user_id) if x_user_id else UUID("24e7d141-6d7c-4e9b-992e-89c944f92ad6")
    """
    Create a new VRP job and enqueue for processing
    """
    # Create job in database
    job = db_service.create_vrp_job(
        db,
        requestor_user_id=user_id,
        params=job_create.model_dump()
    )
    
    # Enqueue Celery task
    from app.celery_worker import solve_vrp
    solve_vrp.delay(str(job.id))
    
    return VRPJobResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at
    )


@router.get("/jobs", response_model=VRPJobListResponse)
async def list_vrp_jobs(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user_id = UUID(x_user_id) if x_user_id else UUID("24e7d141-6d7c-4e9b-992e-89c944f92ad6")
    """
    List VRP jobs for the current user
    """
    skip = (page - 1) * page_size
    
    jobs = db_service.get_vrp_jobs(
        db,
        requestor_user_id=user_id,
        status=status,
        skip=skip,
        limit=page_size
    )
    
    # Count total (simplified - in production use count query)
    total = len(jobs)
    
    # Use summary schema (excludes large result field)
    job_summaries = [VRPJobSummary.model_validate(job) for job in jobs]
    
    return VRPJobListResponse(
        jobs=job_summaries,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/jobs/{job_id}", response_model=VRPJobDetail)
async def get_vrp_job(
    job_id: UUID,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get VRP job details
    """
    job = db_service.get_vrp_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return VRPJobDetail.model_validate(job)


@router.post("/jobs/{job_id}/finalize")
async def finalize_vrp_job(
    job_id: UUID,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Finalize VRP job assignments (idempotent)
    """
    job = db_service.get_vrp_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if already finalized
    if job.status == "finalized":
        return {"message": "Job already finalized", "job_id": str(job_id)}
    
    # Check if ready to finalize
    if job.status != "ready_to_preview":
        raise HTTPException(
            status_code=409,
            detail=f"Job must be in 'ready_to_preview' status to finalize. Current status: {job.status}"
        )
    
    # Finalize assignments
    db_service.finalize_job_assignments(db, job_id)
    
    return {"message": "Job finalized successfully", "job_id": str(job_id)}
