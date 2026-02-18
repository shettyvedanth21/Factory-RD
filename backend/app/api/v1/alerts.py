from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models import User, Rule, Device
from app.schemas.alert import AlertResponse
from app.repositories import alert_repo


router = APIRouter(tags=["Alerts"])
logger = get_logger(__name__)


@router.get("/alerts", response_model=dict)
async def list_alerts(
    device_id: Optional[int] = Query(None),
    severity: Optional[Literal["low", "medium", "high", "critical"]] = Query(None),
    resolved: Optional[bool] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all alerts for the current factory.
    
    Can filter by device_id, severity, resolved status, and date range.
    """
    factory_id = user._token_factory_id
    
    alerts, total = await alert_repo.get_all(
        db, factory_id, device_id, severity, resolved, start, end, page, per_page
    )
    
    # Build response with rule and device names
    alerts_data = []
    for alert in alerts:
        # Get rule and device details
        rule_result = await db.execute(
            select(Rule).where(Rule.id == alert.rule_id)
        )
        rule = rule_result.scalar_one_or_none()
        
        device_result = await db.execute(
            select(Device).where(Device.id == alert.device_id)
        )
        device = device_result.scalar_one_or_none()
        
        alert_dict = AlertResponse.model_validate(alert).model_dump()
        alert_dict["rule_name"] = rule.name if rule else None
        alert_dict["device_name"] = device.name if device else None
        alerts_data.append(alert_dict)
    
    return {
        "data": alerts_data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/alerts/{alert_id}", response_model=dict)
async def get_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert details.
    
    Returns 404 if alert not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    alert = await alert_repo.get_by_id(db, factory_id, alert_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Get rule and device details
    rule_result = await db.execute(
        select(Rule).where(Rule.id == alert.rule_id)
    )
    rule = rule_result.scalar_one_or_none()
    
    device_result = await db.execute(
        select(Device).where(Device.id == alert.device_id)
    )
    device = device_result.scalar_one_or_none()
    
    alert_dict = AlertResponse.model_validate(alert).model_dump()
    alert_dict["rule_name"] = rule.name if rule else None
    alert_dict["device_name"] = device.name if device else None
    
    return {"data": alert_dict}


@router.patch("/alerts/{alert_id}/resolve", response_model=dict)
async def resolve_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve an alert.
    
    Returns 404 if alert not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    alert = await alert_repo.resolve(db, factory_id, alert_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    logger.info(
        "alert.resolved",
        factory_id=factory_id,
        alert_id=alert_id,
        user_id=user.id
    )
    
    # Get rule and device details
    rule_result = await db.execute(
        select(Rule).where(Rule.id == alert.rule_id)
    )
    rule = rule_result.scalar_one_or_none()
    
    device_result = await db.execute(
        select(Device).where(Device.id == alert.device_id)
    )
    device = device_result.scalar_one_or_none()
    
    alert_dict = AlertResponse.model_validate(alert).model_dump()
    alert_dict["rule_name"] = rule.name if rule else None
    alert_dict["device_name"] = device.name if device else None
    
    return {"data": alert_dict}
