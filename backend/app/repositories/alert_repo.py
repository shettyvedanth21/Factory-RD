from typing import Optional, Tuple, Literal
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, Rule, Device, RuleCooldown


async def create_alert(
    db: AsyncSession,
    factory_id: int,
    rule_id: int,
    device_id: int,
    triggered_at: datetime,
    severity: str,
    message: Optional[str] = None,
    snapshot: Optional[dict] = None
) -> Alert:
    """
    Create a new alert.
    
    Args:
        db: Database session
        factory_id: Factory ID
        rule_id: Rule ID
        device_id: Device ID
        triggered_at: Trigger timestamp
        severity: Alert severity
        message: Alert message
        snapshot: Telemetry snapshot
    
    Returns:
        Created alert
    """
    alert = Alert(
        factory_id=factory_id,
        rule_id=rule_id,
        device_id=device_id,
        triggered_at=triggered_at,
        severity=severity,
        message=message,
        telemetry_snapshot=snapshot,
        notification_sent=False
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_all(
    db: AsyncSession,
    factory_id: int,
    device_id: Optional[int] = None,
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None,
    resolved: Optional[bool] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 20
) -> Tuple[list[Alert], int]:
    """
    Get all alerts for a factory with filtering and pagination.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        device_id: Filter by device
        severity: Filter by severity
        resolved: Filter by resolved status
        start: Filter by start date
        end: Filter by end date
        page: Page number
        per_page: Items per page
    
    Returns:
        Tuple of (alerts list, total count)
    """
    # Base query with factory isolation
    query = select(Alert).where(Alert.factory_id == factory_id)
    
    # Apply filters
    if device_id is not None:
        query = query.where(Alert.device_id == device_id)
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    if resolved is not None:
        if resolved:
            query = query.where(Alert.resolved_at.is_not(None))
        else:
            query = query.where(Alert.resolved_at.is_(None))
    
    if start:
        query = query.where(Alert.triggered_at >= start)
    
    if end:
        query = query.where(Alert.triggered_at <= end)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = (
        query
        .offset((page - 1) * per_page)
        .limit(per_page)
        .order_by(Alert.triggered_at.desc())
    )
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return list(alerts), total or 0


async def get_by_id(
    db: AsyncSession,
    factory_id: int,
    alert_id: int
) -> Optional[Alert]:
    """
    Get an alert by ID within a factory.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        alert_id: Alert ID
    
    Returns:
        Alert object or None if not found
    """
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.factory_id == factory_id  # Factory isolation
        )
    )
    return result.scalar_one_or_none()


async def resolve(
    db: AsyncSession,
    factory_id: int,
    alert_id: int
) -> Optional[Alert]:
    """
    Resolve an alert.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        alert_id: Alert ID
    
    Returns:
        Resolved alert or None if not found
    """
    alert = await get_by_id(db, factory_id, alert_id)
    if not alert:
        return None
    
    alert.resolved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_cooldown(
    db: AsyncSession,
    rule_id: int,
    device_id: int
) -> Optional[RuleCooldown]:
    """
    Get cooldown record for a rule-device combination.
    
    Args:
        db: Database session
        rule_id: Rule ID
        device_id: Device ID
    
    Returns:
        RuleCooldown object or None if not found
    """
    result = await db.execute(
        select(RuleCooldown).where(
            RuleCooldown.rule_id == rule_id,
            RuleCooldown.device_id == device_id
        )
    )
    return result.scalar_one_or_none()


async def upsert_cooldown(
    db: AsyncSession,
    rule_id: int,
    device_id: int,
    last_triggered: datetime
) -> None:
    """
    Upsert cooldown record.
    
    Args:
        db: Database session
        rule_id: Rule ID
        device_id: Device ID
        last_triggered: Last trigger timestamp
    """
    # Check if cooldown exists
    cooldown = await get_cooldown(db, rule_id, device_id)
    
    if cooldown:
        # Update existing
        cooldown.last_triggered = last_triggered
    else:
        # Create new
        cooldown = RuleCooldown(
            rule_id=rule_id,
            device_id=device_id,
            last_triggered=last_triggered
        )
        db.add(cooldown)
    
    await db.commit()
