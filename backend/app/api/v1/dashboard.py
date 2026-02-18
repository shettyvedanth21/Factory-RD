from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, Device, Alert


router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/summary", response_model=dict)
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary statistics.
    
    Returns:
    - total_devices: Total device count
    - active_devices: Devices with is_active=True
    - total_alerts: Total unresolved alert count
    - critical_alerts: Unresolved critical alerts count
    """
    factory_id = user._token_factory_id
    
    # Get total devices
    total_devices_result = await db.execute(
        select(func.count()).select_from(Device).where(
            Device.factory_id == factory_id
        )
    )
    total_devices = total_devices_result.scalar() or 0
    
    # Get active devices
    active_devices_result = await db.execute(
        select(func.count()).select_from(Device).where(
            Device.factory_id == factory_id,
            Device.is_active == True
        )
    )
    active_devices = active_devices_result.scalar() or 0
    
    # Get total unresolved alerts
    total_alerts_result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.factory_id == factory_id,
            Alert.resolved_at == None
        )
    )
    total_alerts = total_alerts_result.scalar() or 0
    
    # Get critical unresolved alerts
    critical_alerts_result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.factory_id == factory_id,
            Alert.resolved_at == None,
            Alert.severity == "critical"
        )
    )
    critical_alerts = critical_alerts_result.scalar() or 0
    
    return {
        "data": {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts
        }
    }
