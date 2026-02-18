from typing import Dict, Union
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from telemetry.logging_config import get_logger

logger = get_logger(__name__)


async def discover_parameters(
    db: AsyncSession,
    factory_id: int,
    device_id: int,
    metrics: Dict[str, Union[float, int]]
) -> dict[str, bool]:
    """
    Upsert all metric keys into device_parameters table.
    Uses INSERT ... ON DUPLICATE KEY UPDATE for idempotency.
    
    Args:
        db: Database session
        factory_id: Factory ID for isolation
        device_id: Device ID
        metrics: Dictionary of parameter keys and values
    
    Returns:
        Dictionary mapping parameter_key to is_newly_discovered boolean
    
    Example:
        metrics = {"temperature": 45.5, "pressure": 101.3}
        result = await discover_parameters(db, 1, 1, metrics)
        # result = {"temperature": True, "pressure": False}
    """
    newly_discovered = {}
    now = datetime.utcnow()
    
    for key, value in metrics.items():
        # Determine data type from value
        if isinstance(value, float):
            data_type = "float"
        elif isinstance(value, int):
            data_type = "int"
        else:
            data_type = "string"
        
        # INSERT ... ON DUPLICATE KEY UPDATE
        # MySQL returns rowcount=1 for insert, rowcount=2 for update (when ON DUPLICATE KEY UPDATE changes a value)
        # However, if no values change, rowcount=0
        # We need to check if the row existed before
        
        # First check if parameter exists
        check_query = text("""
            SELECT id FROM device_parameters 
            WHERE device_id = :device_id AND parameter_key = :parameter_key
        """)
        result = await db.execute(
            check_query,
            {"device_id": device_id, "parameter_key": key}
        )
        exists = result.scalar_one_or_none() is not None
        
        # Upsert query
        upsert_query = text("""
            INSERT INTO device_parameters 
                (factory_id, device_id, parameter_key, data_type, is_kpi_selected, discovered_at, updated_at)
            VALUES 
                (:factory_id, :device_id, :parameter_key, :data_type, :is_kpi_selected, :discovered_at, :updated_at)
            ON DUPLICATE KEY UPDATE
                updated_at = :updated_at
        """)
        
        await db.execute(
            upsert_query,
            {
                "factory_id": factory_id,
                "device_id": device_id,
                "parameter_key": key,
                "data_type": data_type,
                "is_kpi_selected": True,
                "discovered_at": now,
                "updated_at": now
            }
        )
        
        # Mark as newly discovered if it didn't exist before
        is_new = not exists
        newly_discovered[key] = is_new
        
        if is_new:
            logger.info(
                "parameter.discovered",
                factory_id=factory_id,
                device_id=device_id,
                parameter=key,
                data_type=data_type
            )
    
    await db.commit()
    
    return newly_discovered
