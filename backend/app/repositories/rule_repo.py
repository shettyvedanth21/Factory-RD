from typing import Optional, Tuple, Literal
from datetime import datetime

from sqlalchemy import select, func, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Rule, Device, rule_devices


async def get_all(
    db: AsyncSession,
    factory_id: int,
    device_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    scope: Optional[Literal["device", "global"]] = None,
    page: int = 1,
    per_page: int = 20
) -> Tuple[list[Rule], int]:
    """
    Get all rules for a factory with filtering and pagination.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        device_id: Filter by device (returns global + device-specific rules)
        is_active: Filter by active status
        scope: Filter by scope (device/global)
        page: Page number
        per_page: Items per page
    
    Returns:
        Tuple of (rules list, total count)
    """
    # Base query with factory isolation
    query = select(Rule).where(Rule.factory_id == factory_id)
    
    # Apply filters
    if is_active is not None:
        query = query.where(Rule.is_active == is_active)
    
    if scope:
        query = query.where(Rule.scope == scope)
    
    if device_id is not None:
        # Get global rules + rules that include this device
        query = query.where(
            (Rule.scope == "global") |
            (Rule.devices.any(Device.id == device_id))
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination and load devices relationship
    query = (
        query
        .options(selectinload(Rule.devices))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .order_by(Rule.created_at.desc())
    )
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return list(rules), total or 0


async def get_by_id(
    db: AsyncSession,
    factory_id: int,
    rule_id: int
) -> Optional[Rule]:
    """
    Get a rule by ID within a factory.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        rule_id: Rule ID
    
    Returns:
        Rule object or None if not found
    """
    result = await db.execute(
        select(Rule)
        .options(selectinload(Rule.devices))
        .where(
            Rule.id == rule_id,
            Rule.factory_id == factory_id  # Factory isolation
        )
    )
    return result.scalar_one_or_none()


async def get_active_for_device(
    db: AsyncSession,
    factory_id: int,
    device_id: int
) -> list[Rule]:
    """
    Get all active rules for a device.
    Returns global rules + device-specific rules.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        device_id: Device ID
    
    Returns:
        List of active rules applicable to this device
    """
    result = await db.execute(
        select(Rule)
        .where(
            Rule.factory_id == factory_id,  # Factory isolation
            Rule.is_active == True,
            (Rule.scope == "global") |
            (Rule.devices.any(Device.id == device_id))
        )
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    factory_id: int,
    user_id: int,
    data: dict
) -> Rule:
    """
    Create a new rule.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        user_id: User ID creating the rule
        data: Rule data
    
    Returns:
        Created rule
    """
    # Extract device_ids for relationship
    device_ids = data.pop("device_ids", [])
    
    # Create rule
    rule = Rule(
        factory_id=factory_id,
        created_by=user_id,
        **data
    )
    db.add(rule)
    await db.flush()
    
    # Add device associations if device scope
    if device_ids and data.get("scope") == "device":
        # Get devices that belong to this factory
        devices_result = await db.execute(
            select(Device).where(
                Device.factory_id == factory_id,
                Device.id.in_(device_ids)
            )
        )
        devices = devices_result.scalars().all()
        rule.devices.extend(devices)
    
    await db.commit()
    await db.refresh(rule)
    return rule


async def update(
    db: AsyncSession,
    factory_id: int,
    rule_id: int,
    data: dict
) -> Optional[Rule]:
    """
    Update a rule.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        rule_id: Rule ID
        data: Update data
    
    Returns:
        Updated rule or None if not found
    """
    # Get rule with factory isolation
    rule = await get_by_id(db, factory_id, rule_id)
    if not rule:
        return None
    
    # Extract device_ids for relationship update
    device_ids = data.pop("device_ids", None)
    
    # Update scalar fields
    for key, value in data.items():
        setattr(rule, key, value)
    
    # Update device associations if provided
    if device_ids is not None and rule.scope == "device":
        # Clear existing associations
        rule.devices.clear()
        
        # Add new associations
        devices_result = await db.execute(
            select(Device).where(
                Device.factory_id == factory_id,
                Device.id.in_(device_ids)
            )
        )
        devices = devices_result.scalars().all()
        rule.devices.extend(devices)
    
    rule.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete(
    db: AsyncSession,
    factory_id: int,
    rule_id: int
) -> bool:
    """
    Delete a rule.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        rule_id: Rule ID
    
    Returns:
        True if deleted, False if not found
    """
    # Verify rule exists and belongs to factory
    rule = await get_by_id(db, factory_id, rule_id)
    if not rule:
        return False
    
    await db.delete(rule)
    await db.commit()
    return True


async def toggle(
    db: AsyncSession,
    factory_id: int,
    rule_id: int
) -> Optional[Rule]:
    """
    Toggle rule active status.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        rule_id: Rule ID
    
    Returns:
        Updated rule or None if not found
    """
    rule = await get_by_id(db, factory_id, rule_id)
    if not rule:
        return None
    
    rule.is_active = not rule.is_active
    rule.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rule)
    return rule
