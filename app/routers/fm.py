from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.dependencies import get_current_user_id, verify_user_exists
from app.schemas import FMLocationUpdate
from app.services.redis_service import redis_service
from app.models import User

router = APIRouter(prefix="/api/v1/fm", tags=["Field Men"])


@router.post("/location")
async def update_fm_location(
    location: FMLocationUpdate,
    user_id: UUID = Depends(get_current_user_id),
    user: User = Depends(verify_user_exists),
    db: Session = Depends(get_db)
):
    """
    Update field man current location in Redis cache
    """
    # Verify user is FM role
    if user.role != "fm":
        raise HTTPException(
            status_code=403,
            detail="Only field men can update locations"
        )
    
    redis_service.set_fm_location(
        str(user_id),
        location.current_lat,
        location.current_long
    )
    
    return {
        "message": "Location updated successfully",
        "user_id": str(user_id),
        "lat": location.current_lat,
        "long": location.current_long
    }
