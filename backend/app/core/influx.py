from typing import List, Optional

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write_api_async import WriteApiAsync

from .config import settings


# InfluxDB client instance
_influx_client: Optional[InfluxDBClientAsync] = None
_write_api: Optional[WriteApiAsync] = None


async def get_influx_client() -> InfluxDBClientAsync:
    """
    Get or create the InfluxDB client instance.
    
    Returns:
        InfluxDB async client
    """
    global _influx_client
    
    if _influx_client is None:
        _influx_client = InfluxDBClientAsync(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org
        )
    
    return _influx_client


async def get_write_api() -> WriteApiAsync:
    """
    Get or create the InfluxDB write API.
    
    Returns:
        InfluxDB write API
    """
    global _write_api
    
    if _write_api is None:
        client = await get_influx_client()
        _write_api = client.write_api()
    
    return _write_api


async def write_points(points: List[Point], precision: str = "s") -> None:
    """
    Write data points to InfluxDB.
    
    Args:
        points: List of InfluxDB Point objects
        precision: Time precision (s=seconds, ms=milliseconds, etc.)
    """
    write_api = await get_write_api()
    await write_api.write(
        bucket=settings.influxdb_bucket,
        org=settings.influxdb_org,
        record=points,
        write_precision=precision
    )


async def query(flux: str) -> list:
    """
    Execute a Flux query against InfluxDB.
    
    Args:
        flux: Flux query string
    
    Returns:
        List of FluxRecord objects
    """
    client = await get_influx_client()
    query_api = client.query_api()
    
    result = await query_api.query(flux, org=settings.influxdb_org)
    
    # Flatten results
    records = []
    for table in result:
        records.extend(table.records)
    
    return records


async def check_influx_health() -> bool:
    """
    Check InfluxDB connectivity.
    
    Returns:
        True if InfluxDB is accessible, False otherwise
    """
    try:
        client = await get_influx_client()
        health = await client.health()
        return health.status == "pass"
    except Exception:
        return False


async def close_influx():
    """Close the InfluxDB connection (call on shutdown)."""
    global _influx_client, _write_api
    
    if _write_api:
        await _write_api.close()
        _write_api = None
    
    if _influx_client:
        await _influx_client.close()
        _influx_client = None
