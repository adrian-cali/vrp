from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class FMLocationUpdate(BaseModel):
    current_lat: float = Field(..., ge=-90, le=90)
    current_long: float = Field(..., ge=-180, le=180)


class VRPJobCreate(BaseModel):
    strategy: str = "manual_area"
    area_id: Optional[UUID] = None
    max_tasks: int = Field(10000, le=10000)
    priority_min: float = Field(1, ge=1, le=100)
    priority_max: float = Field(100, ge=1, le=100)
    fm_user_ids: Optional[List[UUID]] = None
    h3_resolution: Optional[int] = Field(8, ge=0, le=15)


class VRPJobResponse(BaseModel):
    job_id: UUID
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class VRPJobDetail(BaseModel):
    id: UUID
    requestor_user_id: UUID
    status: str
    params: dict
    result: Optional[dict]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VRPJobSummary(BaseModel):
    """Lightweight job summary for list view (excludes large result field)"""
    id: UUID
    requestor_user_id: UUID
    status: str
    params: dict
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VRPJobListResponse(BaseModel):
    jobs: List[VRPJobSummary]  # Use summary instead of detail
    total: int
    page: int
    page_size: int
