from datetime import datetime
from typing import List, Dict, Union

from influxdb_client import Point
from influxdb_client.client.write_api_async import WriteApiAsync

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


def build_points(
    factory_id: int,
    device_id: int,
    metrics: Dict[str, Union[float, int]],
    timestamp: datetime
) -> List[Point]:
    """
    Build InfluxDB Point objects from telemetry metrics.
    
    Each metric becomes a separate point with tags:
    - factory_id: Factory ID for isolation
    - device_id: Device ID
    - parameter: Parameter name (e.g., "temperature")
    
    Args:
        factory_id: Factory ID
        device_id: Device ID
        metrics: Dictionary of parameter keys and numeric values
        timestamp: Timestamp for the measurements
    
    Returns:
        List of InfluxDB Point objects
    
    Note:
        Never raises exceptions. Logs warnings for invalid points.
    """
    points = []
    
    for param_key, value in metrics.items():
        try:
            point = (
                Point("device_metrics")
                .tag("factory_id", str(factory_id))
                .tag("device_id", str(device_id))
                .tag("parameter", param_key)
                .field("value", float(value))
                .time(timestamp)
            )
            points.append(point)
        except Exception as e:
            logger.warning(
                "point.build_failed",
                factory_id=factory_id,
                device_id=device_id,
                parameter=param_key,
                error=str(e)
            )
            # Continue processing other points
            continue
    
    return points


async def write_batch(write_api: WriteApiAsync, points: List[Point]) -> None:
    """
    Write a batch of points to InfluxDB.
    
    Args:
        write_api: InfluxDB write API instance
        points: List of Point objects to write
    
    Note:
        Never raises exceptions. Logs errors but does not crash.
        Telemetry loss is acceptable; crash is not.
    """
    if not points:
        return
    
    try:
        await write_api.write(
            bucket=settings.influxdb_bucket,
            org=settings.influxdb_org,
            record=points
        )
        logger.debug(
            "influx.batch_written",
            point_count=len(points)
        )
    except Exception as e:
        logger.error(
            "influx.write_failed",
            point_count=len(points),
            error=str(e)
        )
        # Do NOT raise — telemetry loss is acceptable; crash is not
