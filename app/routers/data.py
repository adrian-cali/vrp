from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Task, FMHomeLocation
from app.services.h3_service import h3_service
from app.config import settings

router = APIRouter(tags=["Data"])


@router.get("/tasks")
async def get_tasks(
    limit: int = Query(1000, le=10000),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get tasks (for map visualization) - Public endpoint"""
    query = db.query(Task)
    
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.limit(limit).all()
    
    return [{
        "id": str(task.id),
        "address": task.address,
        "latitude": task.latitude,
        "longitude": task.longitude,
        "priority": task.priority,
        "status": task.status
    } for task in tasks]


@router.get("/fm_home_locations")
async def get_fm_home_locations(
    limit: int = Query(1000, le=10000),
    db: Session = Depends(get_db)
):
    """Get FM home locations (for map visualization) - Public endpoint"""
    fms = db.query(FMHomeLocation).limit(limit).all()
    
    return [{
        "user_id": str(fm.user_id),
        "address": fm.address,
        "home_lat": fm.home_lat,
        "home_long": fm.home_long
    } for fm in fms]


@router.get("/h3_clusters")
async def get_h3_clusters(
    limit: int = Query(1000, le=10000),
    db: Session = Depends(get_db)
):
    """Get H3 cluster visualization data - Public endpoint"""
    
    if not settings.h3_enabled:
        return {"enabled": False, "clusters": []}
    
    # Get tasks
    tasks = db.query(Task).filter(
        Task.latitude.isnot(None),
        Task.longitude.isnot(None)
    ).limit(limit).all()
    
    if not tasks:
        return {"enabled": True, "clusters": []}
    
    # Convert to dicts
    task_dicts = [{
        "id": str(t.id),
        "latitude": t.latitude,
        "longitude": t.longitude,
        "priority": t.priority
    } for t in tasks]
    
    # Cluster
    clusters = h3_service.cluster_tasks_by_h3(task_dicts)
    
    # Format response
    cluster_data = []
    for cell_id, task_list in clusters.items():
        center_lat, center_lng = h3_service.get_cluster_center(cell_id)
        cluster_data.append({
            "cell_id": cell_id,
            "center_lat": center_lat,
            "center_lng": center_lng,
            "task_count": len(task_list),
            "avg_priority": sum(t["priority"] for t in task_list) / len(task_list) if task_list else 0,
            "task_ids": [t["id"] for t in task_list]
        })
    
    return {
        "enabled": True,
        "resolution": settings.h3_resolution,
        "total_clusters": len(clusters),
        "total_tasks": len(tasks),
        "clusters": cluster_data
    }
