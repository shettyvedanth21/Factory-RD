from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceParameter


async def get_all(
    db: AsyncSession,
    factory_id: int,
    device_id: int
) -> list[DeviceParameter]:
    """
    Get all parameters for a device.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        device_id: Device ID
    
    Returns:
        List of device parameters
    
    Note:
        Filters by factory_id to ensure factory isolation
    """
    result = await db.execute(
        select(DeviceParameter).where(
            DeviceParameter.factory_id == factory_id,  # Factory isolation
            DeviceParameter.device_id == device_id
        ).order_by(DeviceParameter.parameter_key)
    )
    return list(result.scalars().all())


async def get_selected_keys(
    db: AsyncSession,
    factory_id: int,
    device_id: int
) -> list[str]:
    """
    Get parameter keys that are selected as KPIs.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        device_id: Device ID
    
    Returns:
        List of parameter keys where is_kpi_selected=True
    """
    result = await db.execute(
        select(DeviceParameter.parameter_key).where(
            DeviceParameter.factory_id == factory_id,  # Factory isolation
            DeviceParameter.device_id == device_id,
            DeviceParameter.is_kpi_selected == True
        )
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession,
    factory_id: int,
    device_id: int,
    param_id: int,
    data: dict
) -> Optional[DeviceParameter]:
    """
    Update a device parameter.
    
    Args:
        db: Database session
        factory_id: Factory ID (MUST be from JWT)
        device_id: Device ID
        param_id: Parameter ID
        data: Update data dictionary
    
    Returns:
        Updated parameter or None if not found
    
    Note:
        Returns None if parameter exists but belongs to different factory/device
    """
    # Get parameter with factory isolation
    result = await db.execute(
        select(DeviceParameter).where(
            DeviceParameter.id == param_id,
            DeviceParameter.factory_id == factory_id,  # Factory isolation
            DeviceParameter.device_id == device_id
        )
    )
    parameter = result.scalar_one_or_none()
    
    if not parameter:
        return None
    
    # Update fields
    for key, value in data.items():
        setattr(parameter, key, value)
    
    parameter.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(parameter)
    return parameter
