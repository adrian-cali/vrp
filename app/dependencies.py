from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.database import get_db
from app.services.db_service import db_service


async def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> UUID:
    """Validate and return current user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format for X-User-Id")
    
    return user_id


async def verify_user_exists(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Verify user exists in database"""
    user = db_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
