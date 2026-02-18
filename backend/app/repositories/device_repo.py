from typing import Optional, Tuple
from datetime import datetime

from sqlalchemy import select, func, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device


async def get_all(
    db: AsyncSession,
    factory_id: int,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Tuple[list[Device], int]:
    """
    Get all devices for a factory with pagination and filtering.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT, never from request body)
        page: Page number (1-indexed)
        per_page: Items per page
        search: Search query for device_key or name
        is_active: Filter by active status
    
    Returns:
        Tuple of (devices list, total count)
    """
    # Base query with factory_id filter (NON-NEGOTIABLE)
    query = select(Device).where(Device.factory_id == factory_id)
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Device.device_key.ilike(search_filter)) |
            (Device.name.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.where(Device.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Device.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    devices = result.scalars().all()
    
    return list(devices), total or 0


async def get_by_id(
    db: AsyncSession,
    factory_id: int,
    device_id: int
) -> Optional[Device]:
    """
    Get a device by ID within a factory.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        device_id: Device ID
    
    Returns:
        Device object or None if not found
    
    Note:
        Returns None if device exists but belongs to different factory (404, not 403)
    """
    result = await db.execute(
        select(Device).where(
            Device.id == device_id,
            Device.factory_id == factory_id  # Factory isolation
        )
    )
    return result.scalar_one_or_none()


async def get_by_key(
    db: AsyncSession,
    factory_id: int,
    device_key: str
) -> Optional[Device]:
    """
    Get a device by device_key within a factory.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        device_key: Device key
    
    Returns:
        Device object or None if not found
    """
    result = await db.execute(
        select(Device).where(
            Device.device_key == device_key,
            Device.factory_id == factory_id  # Factory isolation
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    factory_id: int,
    data: dict
) -> Device:
    """
    Create a new device.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        data: Device data dictionary
    
    Returns:
        Created device object
    """
    device = Device(
        factory_id=factory_id,  # Always set from JWT
        **data
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def update(
    db: AsyncSession,
    factory_id: int,
    device_id: int,
    data: dict
) -> Optional[Device]:
    """
    Update a device.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        device_id: Device ID
        data: Update data dictionary
    
    Returns:
        Updated device or None if not found
    
    Note:
        Returns None if device exists but belongs to different factory
    """
    # First check if device exists and belongs to factory
    device = await get_by_id(db, factory_id, device_id)
    if not device:
        return None
    
    # Update fields
    for key, value in data.items():
        setattr(device, key, value)
    
    device.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(device)
    return device


async def update_last_seen(
    db: AsyncSession,
    device_id: int,
    timestamp: datetime
) -> None:
    """
    Update device last_seen timestamp.
    
    Args:
        db: Database session
        device_id: Device ID
        timestamp: Last seen timestamp
    
    Note:
        This is called from telemetry pipeline, no factory_id check needed here
    """
    await db.execute(
        sql_update(Device)
        .where(Device.id == device_id)
        .values(last_seen=timestamp)
    )
    await db.commit()
