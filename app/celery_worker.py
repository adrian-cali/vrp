from celery import Celery
from app.config import settings
from app.database import SessionLocal
from app.services.db_service import db_service
from app.services.redis_service import redis_service
from app.services.vroom_service import vroom_service
from app.services.greedy_assignment_service import GreedyAssignmentService
from uuid import UUID
import asyncio
import json

# Create Celery app
celery_app = Celery(
    "vrp_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def convert_uuids_to_strings(obj):
    """Recursively convert all UUID objects to strings for JSON serialization"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_uuids_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_uuids_to_strings(item) for item in obj]
    return obj


@celery_app.task(name="app.celery_worker.solve_vrp")
def solve_vrp(job_id_str: str):
    """
    Celery task to solve VRP using VROOM
    
    Steps:
    1. Mark job running
    2. Load tasks and FM list
    3. Determine vehicle start locations (Redis or home)
    4. Validate coordinates
    5. Build and call VROOM
    6. Normalize output and save assignments
    7. Mark job ready_to_preview
    8. Publish Redis notification
    """
    db = SessionLocal()
    job_id = UUID(job_id_str)
    
    try:
        # 1. Mark job running
        job = db_service.update_vrp_job(db, job_id, status="running")
        if not job:
            raise Exception(f"Job {job_id} not found")
        
        params = job.params
        
        # 2. Load tasks
        tasks = db_service.get_tasks(
            db,
            status="pending",
            max_tasks=params.get("max_tasks", 10000),
            priority_min=params.get("priority_min"),
            priority_max=params.get("priority_max")
        )
        if not tasks:
            raise Exception("No tasks found matching criteria")
        
        # 3. Load FM list
        area_id = params.get("area_id")
        fm_user_ids = params.get("fm_user_ids")
        
        if fm_user_ids:
            fm_user_ids = [UUID(uid) for uid in fm_user_ids]
        
        fms = db_service.get_fm_users(
            db,
            user_ids=fm_user_ids,
            area_id=UUID(area_id) if area_id else None
        )
        
        if not fms:
            raise Exception("No field men found matching criteria")
        
        # 4. Determine vehicle start locations
        fm_locations = {}
        for fm in fms:
            fm_id = str(fm.id)
            
            # Try Redis current location first
            current_loc = redis_service.get_fm_location(fm_id)
            if current_loc:
                fm_locations[fm_id] = (current_loc["lat"], current_loc["long"])
            else:
                # Fall back to home location
                home_loc = db_service.get_fm_home_location(db, fm.id)
                if home_loc:
                    fm_locations[fm_id] = (home_loc.home_lat, home_loc.home_long)
                else:
                    # Skip FM without location
                    continue
        
        if not fm_locations:
            raise Exception("No FM locations available"
)
        
        # 5. Validate task coordinates
        tasks_with_coords = [t for t in tasks if t.latitude and t.longitude]
        if not tasks_with_coords:
            raise Exception("No tasks have valid coordinates")
        
        if len(tasks_with_coords) < len(tasks):
            print(f"Warning: {len(tasks) - len(tasks_with_coords)} tasks skipped due to missing coordinates")
        
        # 5.5 H3 Clustering (if enabled) - Currently for analytics only
        from app.services.h3_service import h3_service
        from app.config import settings
        
        if settings.h3_enabled and len(tasks_with_coords) >= settings.h3_min_tasks:
            print(f"H3 clustering enabled: grouping {len(tasks_with_coords)} tasks...")
            
            # Convert tasks to dicts for h3_service
            task_dicts = [{
                "id": str(t.id),
                "latitude": t.latitude,
                "longitude": t.longitude,
                "priority": t.priority
            } for t in tasks_with_coords]
            
            # Cluster tasks
            clusters = h3_service.cluster_tasks_by_h3(task_dicts)
            print(f"Created {len(clusters)} H3 clusters (resolution {settings.h3_resolution})")
            
            # Assign FMs to clusters
            cluster_assignments = h3_service.assign_fms_to_clusters(clusters, fm_locations)
            
            # Log cluster summary (top 10)
            sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)[:10]
            for cell, task_list in sorted_clusters:
                assigned_fms = cluster_assignments.get(cell, [])
                center_lat, center_lng = h3_service.get_cluster_center(cell)
                print(f"Cluster {cell[:8]}... @ ({center_lat:.4f},{center_lng:.4f}): "
                      f"{len(task_list)} tasks, {len(assigned_fms)} FMs")
        else:
            if settings.h3_enabled:
                print(f"H3 clustering skipped: only {len(tasks_with_coords)} tasks (min required: {settings.h3_min_tasks})")
            else:
                print(f"H3 clustering disabled")
        
        # 6. Use greedy assignment (nearest FM to task)
        print(f"Using greedy assignment for {len(tasks_with_coords)} tasks, {len(fm_locations)} FMs")
        greedy_service = GreedyAssignmentService()
        result = greedy_service.assign_tasks_greedy(
            tasks_with_coords,
            fm_locations,
            max_tasks_per_fm=100
        )
        
        print(f"Greedy assignment complete: {result['summary']['total_tasks_assigned']} assigned, "
              f"{result['summary']['unassigned_tasks']} unassigned")
        
        # 9. Save assignments (use raw result with UUID objects for database)
        assignments_for_db = []
        for assignment in result["assignments"]:
            assignments_for_db.append({
                "vrp_job_id": job_id,  # UUID object (not string)
                "task_id": UUID(assignment["task_id"]),  # Convert string back to UUID
                "fm_user_id": UUID(assignment["fm_user_id"]),  # Convert string back to UUID
                "sequence_no": assignment["sequence_no"],
                "distance_meters": assignment["distance_meters"],
                "eta_seconds": assignment["eta_seconds"],
            })
        
        db_service.create_vrp_assignments(db, assignments_for_db)
        
        # Convert result to strings for JSON storage
        normalized = convert_uuids_to_strings({
            "assignments": result["assignments"],
            "summary": result["summary"]
        })
        
        # 10. Update job with result
        db_service.update_vrp_job(
            db,
            job_id,
            status="ready_to_preview",
            result=normalized
        )
        
        # 11. Publish notification
        redis_service.publish_job_status(str(job_id), "ready_to_preview")
        
        return {
            "job_id": str(job_id),
            "status": "ready_to_preview",
            "tasks_assigned": len(assignments_for_db),
            "fms_used": len(set(a["fm_user_id"] for a in assignments_for_db))
        }
    
    except Exception as e:
        # Mark job as failed
        error_msg = str(e)
        db_service.update_vrp_job(db, job_id, status="failed", error=error_msg)
        redis_service.publish_job_status(str(job_id), "failed")
        raise
    
    finally:
        db.close()
