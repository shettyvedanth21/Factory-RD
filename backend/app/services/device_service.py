import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, Alert
from app.repositories import device_repo, parameter_repo
from app.schemas.device import DeviceListItem, DeviceResponse
from app.schemas.parameter import ParameterResponse


async def calculate_health_score(device: Device, active_alert_count: int) -> int:
    """
    Calculate device health score.
    
    Rules:
    - Start at 100
    - If last_seen is None or > 10 minutes ago: set to 0
    - Decrease by 10 per active alert (minimum 0)
    
    Args:
        device: Device object
        active_alert_count: Number of active alerts
    
    Returns:
        Health score (0-100)
    """
    # Check if device is online
    if not device.last_seen:
        return 0
    
    now = datetime.utcnow()
    online_threshold = now - timedelta(minutes=10)
    
    if device.last_seen < online_threshold:
        return 0
    
    # Start at 100, decrease by 10 per alert
    health_score = 100 - (active_alert_count * 10)
    return max(0, health_score)


async def get_active_alert_count(db: AsyncSession, factory_id: int, device_id: int) -> int:
    """
    Get count of active alerts for a device.
    
    Args:
        db: Database session
        factory_id: Factory ID
        device_id: Device ID
    
    Returns:
        Count of alerts with resolved_at=NULL
    """
    result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.factory_id == factory_id,
            Alert.device_id == device_id,
            Alert.resolved_at == None
        )
    )
    return result.scalar() or 0


async def list_devices(
    db: AsyncSession,
    factory_id: int,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    is_active: Optional[bool] = None
) -> tuple[list[DeviceListItem], int]:
    """
    List devices with computed fields.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        page: Page number
        per_page: Items per page
        search: Search query
        is_active: Filter by active status
    
    Returns:
        Tuple of (device list items, total count)
    """
    # Get devices from repository
    devices, total = await device_repo.get_all(
        db, factory_id, page, per_page, search, is_active
    )
    
    # Build device list items with computed fields
    device_items = []
    for device in devices:
        # Get active alert count
        alert_count = await get_active_alert_count(db, factory_id, device.id)
        
        # Calculate health score
        health_score = await calculate_health_score(device, alert_count)
        
        # TODO: Get current energy from InfluxDB (Phase 3)
        current_energy_kw = 0.0
        
        device_items.append(DeviceListItem(
            id=device.id,
            device_key=device.device_key,
            name=device.name,
            manufacturer=device.manufacturer,
            region=device.region,
            is_active=device.is_active,
            last_seen=device.last_seen,
            health_score=health_score,
            active_alert_count=alert_count,
            current_energy_kw=current_energy_kw
        ))
    
    return device_items, total


async def get_device(
    db: AsyncSession,
    factory_id: int,
    device_id: int
) -> Optional[DeviceResponse]:
    """
    Get device details with parameters.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        device_id: Device ID
    
    Returns:
        DeviceResponse or None if not found
    """
    # Get device
    device = await device_repo.get_by_id(db, factory_id, device_id)
    if not device:
        return None
    
    # Get parameters
    params = await parameter_repo.get_all(db, factory_id, device_id)
    
    # Build response
    response = DeviceResponse.model_validate(device)
    response.parameters = [ParameterResponse.model_validate(p) for p in params]
    
    return response


async def create_device(
    db: AsyncSession,
    factory_id: int,
    data: dict
) -> Device:
    """
    Create a new device.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        data: Device creation data
    
    Returns:
        Created device
    """
    # Generate API key
    api_key = secrets.token_urlsafe(32)
    
    # Add api_key to data
    data['api_key'] = api_key
    
    # Create device
    device = await device_repo.create(db, factory_id, data)
    return device


async def update_device(
    db: AsyncSession,
    factory_id: int,
    device_id: int,
    data: dict
) -> Optional[Device]:
    """
    Update a device.
    
    Args:
        db: Database session
        factory_id: Factory ID (from JWT)
        device_id: Device ID
        data: Update data
    
    Returns:
        Updated device or None if not found
    """
    return await device_repo.update(db, factory_id, device_id, data)
