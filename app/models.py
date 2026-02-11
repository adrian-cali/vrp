import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, ForeignKey, Integer, Index, TIMESTAMP, Double
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    role = Column(Text, nullable=False)  # admin, requestor, fm
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tasks = relationship("Task", back_populates="user")
    fm_home_location = relationship("FMHomeLocation", back_populates="user", uselist=False)
    vrp_jobs = relationship("VRPJob", back_populates="requestor")
    fm_assigned_areas = relationship("FMAssignedArea", back_populates="user")
    vrp_assignments = relationship("VRPAssignment", back_populates="fm_user")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(Text, nullable=False)
    latitude = Column(Double, nullable=True)
    longitude = Column(Double, nullable=True)
    priority = Column(Float, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Text, nullable=False, default="pending")  # pending, assigned, finalized
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    vrp_assignments = relationship("VRPAssignment", back_populates="task")
    
    # Indexes
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_lat_long", "latitude", "longitude"),
    )


class FMHomeLocation(Base):
    __tablename__ = "fm_home_locations"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    address = Column(Text, nullable=True)
    home_lat = Column(Double, nullable=False)
    home_long = Column(Double, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="fm_home_location")


class Area(Base):
    __tablename__ = "areas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)
    
    # Relationships
    fm_assigned_areas = relationship("FMAssignedArea", back_populates="area")


class FMAssignedArea(Base):
    __tablename__ = "fm_assigned_areas"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), primary_key=True)
    
    # Relationships
    user = relationship("User", back_populates="fm_assigned_areas")
    area = relationship("Area", back_populates="fm_assigned_areas")
    
    # Indexes
    __table_args__ = (
        Index("ix_fm_assigned_areas_area_id", "area_id"),
    )


class VRPJob(Base):
    __tablename__ = "vrp_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requestor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Text, nullable=False, default="queued")  # queued, running, ready_to_preview, finalized, failed
    params = Column(JSONB, nullable=False)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    requestor = relationship("User", back_populates="vrp_jobs")
    vrp_assignments = relationship("VRPAssignment", back_populates="vrp_job")
    
    # Indexes
    __table_args__ = (
        Index("ix_vrp_jobs_requestor_user_id", "requestor_user_id"),
        Index("ix_vrp_jobs_status", "status"),
        Index("ix_vrp_jobs_created_at", "created_at"),
    )


class VRPAssignment(Base):
    __tablename__ = "vrp_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vrp_job_id = Column(UUID(as_uuid=True), ForeignKey("vrp_jobs.id"), nullable=False)
    fm_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    sequence_no = Column(Integer, nullable=False)
    eta_seconds = Column(Integer, nullable=True)
    distance_meters = Column(Integer, nullable=True)
    
    # Relationships
    vrp_job = relationship("VRPJob", back_populates="vrp_assignments")
    fm_user = relationship("User", back_populates="vrp_assignments")
    task = relationship("Task", back_populates="vrp_assignments")
    
    # Constraints
    __table_args__ = (
        Index("ix_vrp_assignments_unique", "vrp_job_id", "task_id", unique=True),
    )
