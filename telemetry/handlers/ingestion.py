from datetime import datetime
from typing import Optional

from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from influxdb_client.client.write_api_async import WriteApiAsync

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.models import Device

# Use relative imports when run as module, absolute when run standalone
try:
    from schemas import TelemetryPayload, parse_topic
    from handlers.cache import get_factory_by_slug, get_or_create_device
    from handlers.parameter_discovery import discover_parameters
    from handlers.influx_writer import build_points, write_batch
    from logging_config import get_logger
except ImportError:
    from telemetry.schemas import TelemetryPayload, parse_topic
    from telemetry.handlers.cache import get_factory_by_slug, get_or_create_device
    from telemetry.handlers.parameter_discovery import discover_parameters
    from telemetry.handlers.influx_writer import build_points, write_batch
    from telemetry.logging_config import get_logger


logger = get_logger(__name__)


async def process_telemetry(
    topic: str,
    payload: bytes,
    db: AsyncSession,
    redis: Redis,
    influx_write_api: WriteApiAsync,
) -> None:
    """
    Main telemetry processing pipeline.
    
    This is the core handler that processes incoming MQTT messages.
    It orchestrates the entire pipeline:
    1. Parse topic to extract factory_slug and device_key
    2. Validate payload schema
    3. Resolve factory from cache/DB
    4. Get or auto-create device from cache/DB
    5. Discover new parameters (idempotent)
    6. Write telemetry to InfluxDB
    7. Update device last_seen timestamp
    8. Dispatch rule evaluation to Celery (non-blocking)
    
    CRITICAL: This function MUST catch all exceptions and never raise.
    The MQTT subscriber loop depends on this for stability.
    
    Args:
        topic: MQTT topic string (e.g., "factories/vpc/devices/M01/telemetry")
        payload: Raw message payload bytes
        db: Database session
        redis: Redis client
        influx_write_api: InfluxDB write API
    """
    try:
        # 1. Parse topic to extract factory and device
        try:
            factory_slug, device_key = parse_topic(str(topic))
        except ValueError as e:
            logger.warning(
                "telemetry.invalid_topic",
                topic=str(topic),
                error=str(e)
            )
            return
        
        # 2. Parse and validate payload
        try:
            data = TelemetryPayload.model_validate_json(payload)
        except ValidationError as e:
            logger.warning(
                "telemetry.invalid_payload",
                topic=str(topic),
                factory_slug=factory_slug,
                device_key=device_key,
                error=str(e)
            )
            return
        except Exception as e:
            logger.warning(
                "telemetry.payload_parse_error",
                topic=str(topic),
                factory_slug=factory_slug,
                device_key=device_key,
                error=str(e)
            )
            return
        
        # Use provided timestamp or fallback to server time
        timestamp = data.timestamp or datetime.utcnow()
        
        # 3. Resolve factory (from cache)
        factory = await get_factory_by_slug(redis, db, factory_slug)
        if not factory:
            logger.warning(
                "telemetry.unknown_factory",
                factory_slug=factory_slug,
                device_key=device_key
            )
            return
        
        # 4. Get or create device (from cache, auto-registers if needed)
        device = await get_or_create_device(redis, db, factory.id, device_key)
        
        # 5. Discover new parameters (idempotent)
        await discover_parameters(db, factory.id, device.id, data.metrics)
        
        # 6. Build and write InfluxDB points
        points = build_points(factory.id, device.id, data.metrics, timestamp)
        await write_batch(influx_write_api, points)
        
        # 7. Update device last_seen (fire-and-forget, don't fail pipeline)
        try:
            await db.execute(
                update(Device)
                .where(Device.id == device.id)
                .values(last_seen=timestamp)
            )
            await db.commit()
        except Exception as e:
            logger.warning(
                "telemetry.last_seen_update_failed",
                factory_id=factory.id,
                device_id=device.id,
                error=str(e)
            )
            # Don't fail the pipeline for this
        
        # 8. Dispatch rule evaluation to Celery (non-blocking)
        try:
            from app.workers.rule_engine import evaluate_rules_task
            evaluate_rules_task.delay(
                factory_id=factory.id,
                device_id=device.id,
                metrics=data.metrics,
                timestamp=timestamp.isoformat(),
            )
        except Exception as e:
            logger.warning(
                "telemetry.rule_dispatch_failed",
                factory_id=factory.id,
                device_id=device.id,
                error=str(e)
            )
            # Don't fail the pipeline for this
        
        # Increment Prometheus counter
        try:
            from app.api.v1.metrics import telemetry_messages_total
            telemetry_messages_total.labels(factory_id=str(factory.id)).inc()
        except Exception:
            pass  # Don't fail pipeline if metrics fail
        
        logger.info(
            "telemetry.processed",
            factory_id=factory.id,
            device_id=device.id,
            device_key=device_key,
            metric_count=len(data.metrics),
            timestamp=timestamp.isoformat()
        )
    
    except Exception as e:
        # Final safety net — log and continue, never propagate
        logger.error(
            "telemetry.unhandled_error",
            topic=str(topic),
            error=str(e),
            exc_info=True
        )
        # Do not raise - this would crash the MQTT subscriber loop
