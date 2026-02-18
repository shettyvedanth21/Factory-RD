"""
Analytics API endpoints.
Handles analytics job creation, status polling, and results retrieval.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models import User
from app.models.analytics_job import AnalyticsJob, JobStatus, JobType, JobMode
from app.workers.analytics import run_analytics_job


router = APIRouter(tags=["Analytics"])
logger = get_logger(__name__)


@router.post("/analytics/jobs", status_code=status.HTTP_201_CREATED)
async def create_analytics_job(
    job_type: str,
    device_ids: List[int],
    date_range_start: datetime,
    date_range_end: datetime,
    mode: str = "standard",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new analytics job and dispatch to Celery worker.
    
    Args:
        job_type: Type of analytics (anomaly, failure_prediction, energy_forecast, ai_copilot)
        device_ids: List of device IDs to analyze
        date_range_start: Start of date range (UTC)
        date_range_end: End of date range (UTC)
        mode: Job mode (standard or ai_copilot)
        user: Current authenticated user
        db: Database session
    
    Returns:
        Created job details with job_id
    """
    factory_id = user._token_factory_id
    
    # Validate job_type
    try:
        job_type_enum = JobType(job_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job_type. Must be one of: {[e.value for e in JobType]}",
        )
    
    # Validate mode
    try:
        mode_enum = JobMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid mode. Must be one of: {[e.value for e in JobMode]}",
        )
    
    # Validate date range
    if date_range_start >= date_range_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_range_start must be before date_range_end",
        )
    
    # Validate device_ids
    if not device_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="device_ids cannot be empty",
        )
    
    # Create job
    job_id = str(uuid.uuid4())
    job = AnalyticsJob(
        id=job_id,
        factory_id=factory_id,
        created_by=user.id,
        job_type=job_type_enum,
        mode=mode_enum,
        device_ids=device_ids,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        status=JobStatus.PENDING,
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    logger.info(
        "analytics.job_created",
        factory_id=factory_id,
        job_id=job_id,
        job_type=job_type,
        device_count=len(device_ids),
        user_id=user.id,
    )
    
    # Dispatch Celery task
    run_analytics_job.delay(job_id)
    
    logger.info(
        "analytics.job_dispatched",
        factory_id=factory_id,
        job_id=job_id,
    )
    
    return {
        "data": {
            "id": job.id,
            "factory_id": job.factory_id,
            "job_type": job.job_type.value,
            "mode": job.mode.value,
            "device_ids": job.device_ids,
            "date_range_start": job.date_range_start.isoformat(),
            "date_range_end": job.date_range_end.isoformat(),
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
        }
    }


@router.get("/analytics/jobs")
async def list_analytics_jobs(
    job_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List analytics jobs for the current factory.
    
    Args:
        job_type: Filter by job type
        status_filter: Filter by status
        page: Page number
        per_page: Items per page
        user: Current authenticated user
        db: Database session
    
    Returns:
        Paginated list of jobs
    """
    factory_id = user._token_factory_id
    
    # Build query
    query = select(AnalyticsJob).where(AnalyticsJob.factory_id == factory_id)
    
    # Apply filters
    if job_type:
        try:
            job_type_enum = JobType(job_type)
            query = query.where(AnalyticsJob.job_type == job_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid job_type: {job_type}",
            )
    
    if status_filter:
        try:
            status_enum = JobStatus(status_filter)
            query = query.where(AnalyticsJob.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {status_filter}",
            )
    
    # Order by created_at descending
    query = query.order_by(AnalyticsJob.created_at.desc())
    
    # Count total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(AnalyticsJob).where(
        AnalyticsJob.factory_id == factory_id
    )
    if job_type:
        count_query = count_query.where(AnalyticsJob.job_type == job_type_enum)
    if status_filter:
        count_query = count_query.where(AnalyticsJob.status == status_enum)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "data": [
            {
                "id": job.id,
                "factory_id": job.factory_id,
                "job_type": job.job_type.value,
                "mode": job.mode.value,
                "device_ids": job.device_ids,
                "date_range_start": job.date_range_start.isoformat(),
                "date_range_end": job.date_range_end.isoformat(),
                "status": job.status.value,
                "result_url": job.result_url,
                "error_message": job.error_message,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "created_at": job.created_at.isoformat(),
            }
            for job in jobs
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }


@router.get("/analytics/jobs/{job_id}")
async def get_analytics_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics job details by ID.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        db: Database session
    
    Returns:
        Job details including results if complete
    """
    factory_id = user._token_factory_id
    
    # Fetch job with factory isolation
    result = await db.execute(
        select(AnalyticsJob).where(
            AnalyticsJob.id == job_id,
            AnalyticsJob.factory_id == factory_id,
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        logger.warning(
            "analytics.job_not_found",
            factory_id=factory_id,
            job_id=job_id,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics job not found",
        )
    
    return {
        "data": {
            "id": job.id,
            "factory_id": job.factory_id,
            "job_type": job.job_type.value,
            "mode": job.mode.value,
            "device_ids": job.device_ids,
            "date_range_start": job.date_range_start.isoformat(),
            "date_range_end": job.date_range_end.isoformat(),
            "status": job.status.value,
            "result_url": job.result_url,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_at": job.created_at.isoformat(),
        }
    }


@router.delete("/analytics/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analytics_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete/cancel an analytics job.
    
    Only pending jobs can be cancelled.
    Completed or running jobs cannot be deleted.
    
    Args:
        job_id: Job ID
        user: Current authenticated user
        db: Database session
    """
    factory_id = user._token_factory_id
    
    # Fetch job with factory isolation
    result = await db.execute(
        select(AnalyticsJob).where(
            AnalyticsJob.id == job_id,
            AnalyticsJob.factory_id == factory_id,
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        logger.warning(
            "analytics.delete_job_not_found",
            factory_id=factory_id,
            job_id=job_id,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics job not found",
        )
    
    # Only allow deletion of pending jobs
    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete job with status: {job.status.value}",
        )
    
    # Delete job
    await db.delete(job)
    await db.commit()
    
    logger.info(
        "analytics.job_deleted",
        factory_id=factory_id,
        job_id=job_id,
        user_id=user.id,
    )
