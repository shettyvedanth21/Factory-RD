from datetime import datetime, timedelta
from typing import Optional

from app.core.influx import query as influx_query
from app.core.config import settings
from app.schemas.kpi import KPIValue, DataPoint
from app.models import DeviceParameter


# Constants for staleness detection
LIVE_WINDOW_MINUTES = 5
STALE_THRESHOLD_MINUTES = 10


async def get_live_kpis(
    factory_id: int,
    device_id: int,
    selected_params: list[str],
    param_metadata: dict[str, DeviceParameter]
) -> list[KPIValue]:
    """
    Get live KPI values for a device.
    
    Fetches the most recent value for each selected parameter within the last 5 minutes.
    Marks values as stale if they're older than 10 minutes.
    
    Args:
        factory_id: Factory ID for isolation
        device_id: Device ID
        selected_params: List of parameter keys to fetch
        param_metadata: Dictionary mapping parameter_key to DeviceParameter object
    
    Returns:
        List of KPIValue objects
    """
    if not selected_params:
        return []
    
    # Build Flux query to get last value for each parameter
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: -{LIVE_WINDOW_MINUTES}m)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.device_id == "{device_id}")
  |> last()
'''
    
    try:
        records = await influx_query(flux)
    except Exception:
        # If InfluxDB query fails, return empty list
        return []
    
    # Build KPI values from records
    kpis = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(minutes=STALE_THRESHOLD_MINUTES)
    
    for record in records:
        # Get parameter key from record tags
        param_key = record.get("parameter")
        if not param_key or param_key not in selected_params:
            continue
        
        # Get timestamp and value
        timestamp = record.get("_time")
        value = record.get("_value")
        
        if timestamp is None or value is None:
            continue
        
        # Determine if value is stale
        is_stale = timestamp < stale_threshold
        
        # Get metadata for display name and unit
        param = param_metadata.get(param_key)
        display_name = param.display_name if param else None
        unit = param.unit if param else None
        
        kpis.append(KPIValue(
            parameter_key=param_key,
            display_name=display_name,
            unit=unit,
            value=float(value),
            is_stale=is_stale
        ))
    
    return kpis


def _auto_select_interval(start: datetime, end: datetime) -> str:
    """
    Auto-select aggregation interval based on time range.
    
    Rules:
    - range < 2h → 1m
    - range < 24h → 5m
    - range < 7d → 1h
    - else → 1d
    
    Args:
        start: Start time
        end: End time
    
    Returns:
        Interval string (e.g., "1m", "5m", "1h", "1d")
    """
    duration = end - start
    
    if duration < timedelta(hours=2):
        return "1m"
    elif duration < timedelta(hours=24):
        return "5m"
    elif duration < timedelta(days=7):
        return "1h"
    else:
        return "1d"


async def get_kpi_history(
    factory_id: int,
    device_id: int,
    parameter: str,
    start: datetime,
    end: datetime,
    interval: Optional[str] = None
) -> tuple[list[DataPoint], str]:
    """
    Get historical KPI data for a parameter.
    
    Args:
        factory_id: Factory ID for isolation
        device_id: Device ID
        parameter: Parameter key
        start: Start time
        end: End time
        interval: Aggregation interval (auto-selected if None)
    
    Returns:
        Tuple of (list of DataPoint objects, interval used)
    """
    # Auto-select interval if not provided
    if not interval:
        interval = _auto_select_interval(start, end)
    
    # Build Flux query with aggregation
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.device_id == "{device_id}")
  |> filter(fn: (r) => r.parameter == "{parameter}")
  |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
'''
    
    try:
        records = await influx_query(flux)
    except Exception:
        # If InfluxDB query fails, return empty list
        return [], interval
    
    # Build data points
    points = []
    for record in records:
        timestamp = record.get("_time")
        value = record.get("_value")
        
        if timestamp is None or value is None:
            continue
        
        points.append(DataPoint(
            timestamp=timestamp,
            value=float(value)
        ))
    
    return points, interval
