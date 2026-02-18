from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models import User
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListItem
from app.services import device_service
from app.repositories import device_repo


router = APIRouter(tags=["Devices"])
logger = get_logger(__name__)


@router.get("/devices", response_model=dict)
async def list_devices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all devices for the current factory.
    
    Returns paginated device list with computed fields:
    - health_score: 0-100 based on online status and active alerts
    - active_alert_count: Number of unresolved alerts
    - current_energy_kw: Current energy consumption
    """
    factory_id = user._token_factory_id
    
    devices, total = await device_service.list_devices(
        db, factory_id, page, per_page, search, is_active
    )
    
    return {
        "data": [d.model_dump() for d in devices],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/devices/{device_id}", response_model=dict)
async def get_device(
    device_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get device details including parameters.
    
    Returns 404 if device not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    device = await device_service.get_device(db, factory_id, device_id)
    
    if not device:
        logger.warning(
            "device.not_found",
            factory_id=factory_id,
            device_id=device_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return {"data": device.model_dump()}


@router.post("/devices", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_data: DeviceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new device.
    
    Automatically generates an API key for the device.
    """
    factory_id = user._token_factory_id
    
    # Check if device_key already exists
    existing = await device_repo.get_by_key(db, factory_id, device_data.device_key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device with key '{device_data.device_key}' already exists"
        )
    
    # Create device
    device = await device_service.create_device(
        db, factory_id, device_data.model_dump(exclude_unset=True)
    )
    
    logger.info(
        "device.created",
        factory_id=factory_id,
        device_id=device.id,
        device_key=device.device_key,
        user_id=user.id
    )
    
    return {"data": DeviceResponse.model_validate(device).model_dump()}


@router.patch("/devices/{device_id}", response_model=dict)
async def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a device.
    
    Returns 404 if device not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    device = await device_service.update_device(
        db, factory_id, device_id, device_data.model_dump(exclude_unset=True)
    )
    
    if not device:
        logger.warning(
            "device.update_failed_not_found",
            factory_id=factory_id,
            device_id=device_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    logger.info(
        "device.updated",
        factory_id=factory_id,
        device_id=device_id,
        user_id=user.id
    )
    
    return {"data": DeviceResponse.model_validate(device).model_dump()}


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a device (sets is_active=False).
    
    Returns 404 if device not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    device = await device_service.update_device(
        db, factory_id, device_id, {"is_active": False}
    )
    
    if not device:
        logger.warning(
            "device.delete_failed_not_found",
            factory_id=factory_id,
            device_id=device_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    logger.info(
        "device.deleted",
        factory_id=factory_id,
        device_id=device_id,
        user_id=user.id
    )
