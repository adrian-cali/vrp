from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import json
from app.database import SessionLocal
from app.services.db_service import db_service
from app.services.redis_service import redis_service

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/v1/ws/vrp-jobs/{job_id}")
async def websocket_vrp_job_status(websocket: WebSocket, job_id: UUID, user_id: str = Query(...)):
    """
    WebSocket endpoint for VRP job status notifications
    """
    await websocket.accept()
    
    # Verify user and job
    db = SessionLocal()
    try:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            await websocket.send_json({"error": "Invalid user_id format"})
            await websocket.close()
            return
        
        # Check if user exists
        user = db_service.get_user(db, user_uuid)
        if not user:
            await websocket.send_json({"error": "User not found"})
            await websocket.close()
            return
        
        # Check if job exists and user is requestor
        job = db_service.get_vrp_job(db, job_id)
        if not job:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return
        
        if job.requestor_user_id != user_uuid:
            await websocket.send_json({"error": "Not authorized to view this job"})
            await websocket.close()
            return
        
        # Subscribe to Redis pubsub
        pubsub = redis_service.subscribe_job_status(str(job_id))
        
        # Send initial status
        await websocket.send_json({
            "job_id": str(job_id),
            "status": job.status,
            "message": "Connected to job status updates"
        })
        
        try:
            # Listen for messages
            for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                    
                    # If job is finalized or failed, we can close
                    if data.get("status") in ["finalized", "failed"]:
                        break
        
        except WebSocketDisconnect:
            pass
        finally:
            pubsub.unsubscribe()
            pubsub.close()
    
    finally:
        db.close()
        await websocket.close()
