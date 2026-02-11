from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import User, Task, FMHomeLocation, Area, FMAssignedArea, VRPJob, VRPAssignment
from uuid import UUID


class DBService:
    @staticmethod
    def get_user(db: Session, user_id: UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_fm_users(db: Session, user_ids: Optional[List[UUID]] = None, area_id: Optional[UUID] = None) -> List[User]:
        """Get field men, optionally filtered by user_ids or area"""
        query = db.query(User).filter(User.role == "fm")
        
        if user_ids:
            query = query.filter(User.id.in_(user_ids))
        elif area_id:
            query = query.join(FMAssignedArea).filter(FMAssignedArea.area_id == area_id)
        
        return query.all()
    
    @staticmethod
    def get_fm_home_location(db: Session, user_id: UUID) -> Optional[FMHomeLocation]:
        return db.query(FMHomeLocation).filter(FMHomeLocation.user_id == user_id).first()
    
    @staticmethod
    def get_tasks(
        db: Session,
        status: str = "pending",
        max_tasks: Optional[int] = None,
        priority_min: Optional[float] = None,
        priority_max: Optional[float] = None
    ) -> List[Task]:
        """Get tasks filtered by criteria"""
        query = db.query(Task).filter(Task.status == status)
        
        if priority_min is not None:
            query = query.filter(Task.priority >= priority_min)
        if priority_max is not None:
            query = query.filter(Task.priority <= priority_max)
        
        # Order by priority (1 = highest, 100 = lowest)
        query = query.order_by(Task.priority.asc())
        
        if max_tasks:
            query = query.limit(max_tasks)
        
        return query.all()
    
    @staticmethod
    def create_vrp_job(db: Session, requestor_user_id: UUID, params: dict) -> VRPJob:
        """Create a new VRP job"""
        job = VRPJob(
            requestor_user_id=requestor_user_id,
            status="queued",
            params=params
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def update_vrp_job(
        db: Session,
        job_id: UUID,
        status: Optional[str] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None
    ) -> Optional[VRPJob]:
        """Update VRP job"""
        job = db.query(VRPJob).filter(VRPJob.id == job_id).first()
        if job:
            if status:
                job.status = status
            if result:
                job.result = result
            if error:
                job.error = error
            db.commit()
            db.refresh(job)
        return job
    
    @staticmethod
    def get_vrp_job(db: Session, job_id: UUID) -> Optional[VRPJob]:
        return db.query(VRPJob).filter(VRPJob.id == job_id).first()
    
    @staticmethod
    def get_vrp_jobs(
        db: Session,
        requestor_user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[VRPJob]:
        """Get VRP jobs with pagination"""
        query = db.query(VRPJob)
        
        if requestor_user_id:
            query = query.filter(VRPJob.requestor_user_id == requestor_user_id)
        if status:
            query = query.filter(VRPJob.status == status)
        
        query = query.order_by(VRPJob.created_at.desc())
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create_vrp_assignments(db: Session, assignments: List[dict]) -> None:
        """Bulk create VRP assignments"""
        assignment_objs = [VRPAssignment(**a) for a in assignments]
        db.bulk_save_objects(assignment_objs)
        db.commit()
    
    @staticmethod
    def get_vrp_assignments(db: Session, job_id: UUID) -> List[VRPAssignment]:
        """Get all assignments for a job, ordered by FM and sequence"""
        return db.query(VRPAssignment).filter(
            VRPAssignment.vrp_job_id == job_id
        ).order_by(
            VRPAssignment.fm_user_id,
            VRPAssignment.sequence_no
        ).all()
    
    @staticmethod
    def finalize_job_assignments(db: Session, job_id: UUID) -> None:
        """Finalize job: update task statuses and job status"""
        # Get all assignments for this job
        assignments = db.query(VRPAssignment).filter(VRPAssignment.vrp_job_id == job_id).all()
        task_ids = [a.task_id for a in assignments]
        
        # Update task statuses
        db.query(Task).filter(Task.id.in_(task_ids)).update(
            {"status": "finalized"},
            synchronize_session=False
        )
        
        # Update job status
        db.query(VRPJob).filter(VRPJob.id == job_id).update(
            {"status": "finalized"},
            synchronize_session=False
        )
        
        db.commit()


db_service = DBService()
