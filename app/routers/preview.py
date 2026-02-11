from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.database import get_db
from app.dependencies import get_current_user_id, verify_user_exists
from app.services.db_service import db_service
from app.models import User
from collections import defaultdict

router = APIRouter(prefix="/api/v1/vrp", tags=["VRP Preview"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/jobs/{job_id}/preview", response_class=HTMLResponse)
async def preview_vrp_job(
    request: Request,
    job_id: UUID,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    HTML preview of VRP job assignments grouped by FM
    (Authentication optional - public preview)
    """
    job = db_service.get_vrp_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if ready
    if job.status not in ["ready_to_preview", "finalized"]:
        return templates.TemplateResponse(
            "not_ready.html",
            {"request": request, "job_id": str(job_id), "status": job.status}
        )
    
    # Get assignments
    assignments = db_service.get_vrp_assignments(db, job_id)
    
    # Group by FM
    fm_groups = defaultdict(list)
    for assignment in assignments:
        fm_groups[assignment.fm_user_id].append({
            "sequence_no": assignment.sequence_no,
            "task_id": str(assignment.task_id),
            "address": assignment.task.address,
            "priority": assignment.task.priority,
            "eta_seconds": assignment.eta_seconds,
            "distance_meters": assignment.distance_meters
        })
    
    # Calculate totals per FM
    fm_summaries = []
    for fm_id, tasks in fm_groups.items():
        fm_user = db_service.get_user(db, fm_id)
        total_distance = sum(t.get("distance_meters", 0) for t in tasks if t.get("distance_meters"))
        total_time = sum(t.get("eta_seconds", 0) for t in tasks if t.get("eta_seconds"))
        
        fm_summaries.append({
            "fm_id": str(fm_id),
            "fm_name": fm_user.name if fm_user else "Unknown",
            "task_count": len(tasks),
            "total_distance_km": round(total_distance / 1000, 2) if total_distance else 0,
            "total_time_hours": round(total_time / 3600, 2) if total_time else 0,
            "tasks": sorted(tasks, key=lambda x: x["sequence_no"])
        })
    
    return templates.TemplateResponse(
        "preview.html",
        {
            "request": request,
            "job_id": str(job_id),
            "job_status": job.status,
            "fm_summaries": fm_summaries,
            "total_fms": len(fm_summaries),
            "total_tasks": len(assignments)
        }
    )
