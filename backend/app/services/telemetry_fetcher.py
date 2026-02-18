"""
Telemetry data fetcher for analytics.
Fetches time-series data from InfluxDB and returns as pandas DataFrame.
"""
import json
from datetime import datetime
from typing import List

import pandas as pd

from app.core.config import settings
from app.core.influx import query as influx_query
from app.core.logging import get_logger


logger = get_logger(__name__)


async def fetch_as_dataframe(
    factory_id: int,
    device_ids: List[int],
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    """
    Fetch telemetry data from InfluxDB and return as pandas DataFrame.
    
    Args:
        factory_id: Factory ID for filtering
        device_ids: List of device IDs to fetch data for
        start: Start datetime (UTC)
        end: End datetime (UTC)
    
    Returns:
        DataFrame with columns: timestamp, device_id, then one column per parameter
        Pivoted wide format for easier ML processing
    
    Raises:
        Exception if InfluxDB query fails
    """
    logger.info(
        "telemetry_fetcher.start",
        factory_id=factory_id,
        device_count=len(device_ids),
        start=start.isoformat(),
        end=end.isoformat(),
    )
    
    # Convert device_ids to strings for Flux filter
    device_id_strings = [str(device_id) for device_id in device_ids]
    
    # Build Flux query with factory isolation and device filter
    flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => contains(value: r.device_id, set: {json.dumps(device_id_strings)}))
'''
    
    try:
        records = await influx_query(flux)
        
        if not records:
            logger.warning(
                "telemetry_fetcher.no_data",
                factory_id=factory_id,
                device_ids=device_ids,
            )
            return pd.DataFrame()
        
        logger.info(
            "telemetry_fetcher.records_fetched",
            factory_id=factory_id,
            record_count=len(records),
        )
        
        # Convert records to list of dicts
        data = []
        for record in records:
            data.append({
                "timestamp": record.get("_time"),
                "device_id": int(record.get("device_id", 0)),
                "parameter": record.get("parameter"),
                "value": record.get("_value"),
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
        
        # Convert timestamp to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Pivot to wide format: each parameter becomes a column
        # This makes it easier for ML models to work with
        df_pivot = df.pivot_table(
            index=["timestamp", "device_id"],
            columns="parameter",
            values="value",
            aggfunc="mean",  # Average if multiple values per timestamp
        ).reset_index()
        
        logger.info(
            "telemetry_fetcher.success",
            factory_id=factory_id,
            rows=len(df_pivot),
            columns=len(df_pivot.columns),
            parameters=list(df_pivot.columns[2:]),  # Skip timestamp and device_id
        )
        
        return df_pivot
        
    except Exception as e:
        logger.error(
            "telemetry_fetcher.error",
            factory_id=factory_id,
            error=str(e),
            exc_info=True,
        )
        raise
