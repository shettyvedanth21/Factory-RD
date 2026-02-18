"""
Reports API endpoints.
Handles report creation, status polling, and download.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models import User
from app.models.report import Report, ReportStatus, ReportFormat
from app.workers.reporting import generate_report_task


router = APIRouter(tags=["Reports"])
logger = get_logger(__name__)


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    device_ids: List[int],
    date_range_start: datetime,
    date_range_end: datetime,
    format: str,
    title: Optional[str] = None,
    include_analytics: bool = False,
    analytics_job_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new report and dispatch to Celery worker.
    
    Args:
        device_ids: List of device IDs to include
        date_range_start: Start of date range (UTC)
        date_range_end: End of date range (UTC)
        format: Report format (pdf, excel, json)
        title: Optional report title
        include_analytics: Whether to include analytics results
        analytics_job_id: Analytics job ID if include_analytics is True
        user: Current authenticated user
        db: Database session
    
    Returns:
        Created report details with report_id
    """
    factory_id = user._token_factory_id
    
    # Validate format
    try:
        format_enum = ReportFormat(format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid format. Must be one of: {[e.value for e in ReportFormat]}",
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
    
    # Validate analytics job if requested
    if include_analytics and not analytics_job_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="analytics_job_id required when include_analytics is True",
        )
    
    # Create report
    report_id = str(uuid.uuid4())
    report = Report(
        id=report_id,
        factory_id=factory_id,
        created_by=user.id,
        title=title,
        device_ids=device_ids,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        format=format_enum,
        include_analytics=include_analytics,
        analytics_job_id=analytics_job_id,
        status=ReportStatus.PENDING,
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    logger.info(
        "report.created",
        factory_id=factory_id,
        report_id=report_id,
        format=format,
        device_count=len(device_ids),
        user_id=user.id,
    )
    
    # Dispatch Celery task
    generate_report_task.delay(report_id)
    
    logger.info(
        "report.dispatched",
        factory_id=factory_id,
        report_id=report_id,
    )
    
    return {
        "data": {
            "id": report.id,
            "factory_id": report.factory_id,
            "title": report.title,
            "device_ids": report.device_ids,
            "date_range_start": report.date_range_start.isoformat(),
            "date_range_end": report.date_range_end.isoformat(),
            "format": report.format.value,
            "include_analytics": report.include_analytics,
            "analytics_job_id": report.analytics_job_id,
            "status": report.status.value,
            "created_at": report.created_at.isoformat(),
        }
    }


@router.get("/reports")
async def list_reports(
    format_filter: Optional[str] = Query(None, alias="format"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List reports for the current factory.
    
    Args:
        format_filter: Filter by format
        status_filter: Filter by status
        page: Page number
        per_page: Items per page
        user: Current authenticated user
        db: Database session
    
    Returns:
        Paginated list of reports
    """
    factory_id = user._token_factory_id
    
    # Build query
    query = select(Report).where(Report.factory_id == factory_id)
    
    # Apply filters
    if format_filter:
        try:
            format_enum = ReportFormat(format_filter)
            query = query.where(Report.format == format_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid format: {format_filter}",
            )
    
    if status_filter:
        try:
            status_enum = ReportStatus(status_filter)
            query = query.where(Report.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {status_filter}",
            )
    
    # Order by created_at descending
    query = query.order_by(Report.created_at.desc())
    
    # Count total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(Report).where(
        Report.factory_id == factory_id
    )
    if format_filter:
        count_query = count_query.where(Report.format == format_enum)
    if status_filter:
        count_query = count_query.where(Report.status == status_enum)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return {
        "data": [
            {
                "id": report.id,
                "factory_id": report.factory_id,
                "title": report.title,
                "device_ids": report.device_ids,
                "date_range_start": report.date_range_start.isoformat(),
                "date_range_end": report.date_range_end.isoformat(),
                "format": report.format.value,
                "include_analytics": report.include_analytics,
                "analytics_job_id": report.analytics_job_id,
                "status": report.status.value,
                "file_url": report.file_url,
                "file_size_bytes": report.file_size_bytes,
                "error_message": report.error_message,
                "expires_at": report.expires_at.isoformat() if report.expires_at else None,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get report details by ID.
    
    Args:
        report_id: Report ID
        user: Current authenticated user
        db: Database session
    
    Returns:
        Report details
    """
    factory_id = user._token_factory_id
    
    # Fetch report with factory isolation
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.factory_id == factory_id,
        )
    )
    report = result.scalar_one_or_none()
    
    if not report:
        logger.warning(
            "report.not_found",
            factory_id=factory_id,
            report_id=report_id,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    return {
        "data": {
            "id": report.id,
            "factory_id": report.factory_id,
            "title": report.title,
            "device_ids": report.device_ids,
            "date_range_start": report.date_range_start.isoformat(),
            "date_range_end": report.date_range_end.isoformat(),
            "format": report.format.value,
            "include_analytics": report.include_analytics,
            "analytics_job_id": report.analytics_job_id,
            "status": report.status.value,
            "file_url": report.file_url,
            "file_size_bytes": report.file_size_bytes,
            "error_message": report.error_message,
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
            "created_at": report.created_at.isoformat(),
        }
    }


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download report file (redirects to presigned URL).
    
    Args:
        report_id: Report ID
        user: Current authenticated user
        db: Database session
    
    Returns:
        302 redirect to presigned URL
    """
    factory_id = user._token_factory_id
    
    # Fetch report with factory isolation
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.factory_id == factory_id,
        )
    )
    report = result.scalar_one_or_none()
    
    if not report:
        logger.warning(
            "report.download_not_found",
            factory_id=factory_id,
            report_id=report_id,
            user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    if report.status != ReportStatus.COMPLETE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready for download. Status: {report.status.value}",
        )
    
    if not report.file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file URL not available",
        )
    
    # Check if expired
    if report.expires_at and datetime.utcnow() > report.expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Report has expired",
        )
    
    logger.info(
        "report.download",
        factory_id=factory_id,
        report_id=report_id,
        user_id=user.id,
    )
    
    # Redirect to presigned URL
    return RedirectResponse(url=report.file_url, status_code=status.HTTP_302_FOUND)
