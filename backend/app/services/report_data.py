"""
Report data aggregator.
Fetches and aggregates data from MySQL and InfluxDB for report generation.
"""
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.influx import query as influx_query
from app.core.config import settings
from app.core.logging import get_logger
from app.models.device import Device
from app.models.alert import Alert


logger = get_logger(__name__)


async def get_report_data(
    factory_id: int,
    device_ids: List[int],
    start: datetime,
    end: datetime,
) -> Dict[str, Any]:
    """
    Fetch and aggregate data for report generation.
    
    Args:
        factory_id: Factory ID
        device_ids: List of device IDs to include
        start: Start datetime (UTC)
        end: End datetime (UTC)
    
    Returns:
        Dictionary containing:
        - devices: List of device metadata
        - telemetry_summary: Per-device, per-parameter statistics
        - alerts: List of alerts in date range
        - alert_summary: Alert count by severity
    """
    logger.info(
        "report_data.start",
        factory_id=factory_id,
        device_count=len(device_ids),
        start=start.isoformat(),
        end=end.isoformat(),
    )
    
    async with AsyncSessionLocal() as db:
        # Fetch device metadata with factory isolation
        result = await db.execute(
            select(Device).where(
                Device.factory_id == factory_id,
                Device.id.in_(device_ids),
            )
        )
        devices = result.scalars().all()
        
        devices_data = [
            {
                "id": device.id,
                "name": device.name,
                "device_key": device.device_key,
                "region": device.region,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            }
            for device in devices
        ]
        
        # Fetch alerts in date range with factory isolation
        alert_result = await db.execute(
            select(Alert).where(
                Alert.factory_id == factory_id,
                Alert.device_id.in_(device_ids),
                Alert.triggered_at >= start,
                Alert.triggered_at <= end,
            ).order_by(Alert.triggered_at.desc())
        )
        alerts = alert_result.scalars().all()
        
        alerts_data = [
            {
                "id": alert.id,
                "device_id": alert.device_id,
                "rule_id": alert.rule_id,
                "severity": alert.severity.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            }
            for alert in alerts
        ]
        
        # Alert summary by severity
        alert_summary = {}
        for alert in alerts:
            severity = alert.severity.value
            alert_summary[severity] = alert_summary.get(severity, 0) + 1
    
    # Fetch telemetry summary from InfluxDB
    telemetry_summary = await _get_telemetry_summary(factory_id, device_ids, start, end)
    
    logger.info(
        "report_data.success",
        factory_id=factory_id,
        device_count=len(devices_data),
        alert_count=len(alerts_data),
        telemetry_devices=len(telemetry_summary),
    )
    
    return {
        "devices": devices_data,
        "telemetry_summary": telemetry_summary,
        "alerts": alerts_data,
        "alert_summary": alert_summary,
    }


async def _get_telemetry_summary(
    factory_id: int,
    device_ids: List[int],
    start: datetime,
    end: datetime,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Get telemetry statistics (min, max, avg) per device per parameter.
    
    Returns:
        {
            "device_1": {
                "voltage": {"min": 220.0, "max": 245.0, "avg": 231.4},
                "current": {"min": 2.8, "max": 3.5, "avg": 3.2},
            },
            "device_2": {...}
        }
    """
    import json
    
    device_id_strings = [str(device_id) for device_id in device_ids]
    
    # Build Flux query to get statistics
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => contains(value: r.device_id, set: {json.dumps(device_id_strings)}))
  |> group(columns: ["device_id", "parameter"])
  |> reduce(
      fn: (r, accumulator) => ({{
        min: if r._value < accumulator.min then r._value else accumulator.min,
        max: if r._value > accumulator.max then r._value else accumulator.max,
        sum: accumulator.sum + r._value,
        count: accumulator.count + 1.0
      }}),
      identity: {{min: 999999.0, max: -999999.0, sum: 0.0, count: 0.0}}
    )
  |> map(fn: (r) => ({{
      device_id: r.device_id,
      parameter: r.parameter,
      min: r.min,
      max: r.max,
      avg: r.sum / r.count
    }}))
'''
    
    try:
        records = await influx_query(flux)
        
        # Organize by device_id and parameter
        summary = {}
        for record in records:
            device_id = record.get("device_id", "")
            parameter = record.get("parameter", "")
            
            if device_id not in summary:
                summary[device_id] = {}
            
            summary[device_id][parameter] = {
                "min": float(record.get("min", 0)),
                "max": float(record.get("max", 0)),
                "avg": float(record.get("avg", 0)),
            }
        
        return summary
        
    except Exception as e:
        logger.error(
            "report_data.telemetry_summary_failed",
            factory_id=factory_id,
            error=str(e),
            exc_info=True,
        )
        # Return empty summary on error
        return {}
