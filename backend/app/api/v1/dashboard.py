from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models import User, Device, Alert


router = APIRouter(tags=["Dashboard"])


async def get_current_energy_kw(factory_id: int, db: AsyncSession) -> float:
    """
    Get current total energy consumption from InfluxDB.
    Sums latest 'power' parameter values from last 5 minutes across all devices.
    """
    from app.core.influx import query as influx_query
    
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.parameter == "power")
  |> last()
  |> sum()
'''
    
    try:
        records = await influx_query(flux)
        if records and len(records) > 0:
            # Get sum from aggregated result
            return float(records[0].get("_value", 0.0))
    except Exception:
        pass
    
    return 0.0


async def get_energy_today_kwh(factory_id: int) -> float:
    """Get total energy consumption for today."""
    from app.core.influx import query as influx_query
    
    # Start of today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: {today.isoformat()}Z)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.parameter == "power")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> sum()
'''
    
    try:
        records = await influx_query(flux)
        if records and len(records) > 0:
            # Convert watt-hours to kilowatt-hours
            return float(records[0].get("_value", 0.0)) / 1000.0
    except Exception:
        pass
    
    return 0.0


async def get_energy_this_month_kwh(factory_id: int) -> float:
    """Get total energy consumption for this month."""
    from app.core.influx import query as influx_query
    
    # Start of month
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: {start_of_month.isoformat()}Z)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.parameter == "power")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> sum()
'''
    
    try:
        records = await influx_query(flux)
        if records and len(records) > 0:
            # Convert watt-hours to kilowatt-hours
            return float(records[0].get("_value", 0.0)) / 1000.0
    except Exception:
        pass
    
    return 0.0


@router.get("/dashboard/summary", response_model=dict)
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary statistics.
    
    Returns:
    - total_devices: Total device count
    - active_devices: Devices online (last_seen < 10min)
    - offline_devices: Devices offline
    - active_alerts: Unresolved alerts
    - critical_alerts: Unresolved critical alerts
    - current_energy_kw: Current total power consumption
    - health_score: Overall factory health (0-100)
    - energy_today_kwh: Energy consumed today
    - energy_this_month_kwh: Energy consumed this month
    """
    factory_id = user._token_factory_id
    
    # Get total devices
    total_devices_result = await db.execute(
        select(func.count()).select_from(Device).where(
            Device.factory_id == factory_id
        )
    )
    total_devices = total_devices_result.scalar() or 0
    
    # Get online devices (last_seen < 10 minutes)
    online_threshold = datetime.utcnow() - timedelta(minutes=10)
    active_devices_result = await db.execute(
        select(func.count()).select_from(Device).where(
            Device.factory_id == factory_id,
            Device.is_active == True,
            Device.last_seen >= online_threshold
        )
    )
    active_devices = active_devices_result.scalar() or 0
    
    # Calculate offline devices
    offline_devices = total_devices - active_devices
    
    # Get total unresolved alerts
    active_alerts_result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.factory_id == factory_id,
            Alert.resolved_at == None
        )
    )
    active_alerts = active_alerts_result.scalar() or 0
    
    # Get critical unresolved alerts
    critical_alerts_result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.factory_id == factory_id,
            Alert.resolved_at == None,
            Alert.severity == "critical"
        )
    )
    critical_alerts = critical_alerts_result.scalar() or 0
    
    # Get energy metrics from InfluxDB
    current_energy_kw = await get_current_energy_kw(factory_id, db)
    energy_today_kwh = await get_energy_today_kwh(factory_id)
    energy_this_month_kwh = await get_energy_this_month_kwh(factory_id)
    
    # Calculate health score
    # Formula: 100 - min(30, offline_pct*30) - min(20, alert_rate*10)
    offline_pct = offline_devices / total_devices if total_devices > 0 else 0
    alert_rate = active_alerts / total_devices if total_devices > 0 else 0
    
    offline_penalty = min(30, offline_pct * 30)
    alert_penalty = min(20, alert_rate * 10)
    health_score = max(0, int(100 - offline_penalty - alert_penalty))
    
    return {
        "data": {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "offline_devices": offline_devices,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "current_energy_kw": round(current_energy_kw, 2),
            "health_score": health_score,
            "energy_today_kwh": round(energy_today_kwh, 2),
            "energy_this_month_kwh": round(energy_this_month_kwh, 2)
        }
    }
