from typing import Optional
from datetime import datetime
import json

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.models import Factory, Device
from telemetry.logging_config import get_logger

logger = get_logger(__name__)


def factory_to_json(factory: Factory) -> str:
    """Serialize Factory to JSON for Redis caching."""
    return json.dumps({
        "id": factory.id,
        "name": factory.name,
        "slug": factory.slug,
        "timezone": factory.timezone
    })


def factory_from_json(data: str) -> Factory:
    """Deserialize Factory from JSON."""
    obj = json.loads(data)
    factory = Factory(
        id=obj["id"],
        name=obj["name"],
        slug=obj["slug"],
        timezone=obj["timezone"]
    )
    return factory


def device_to_json(device: Device) -> str:
    """Serialize Device to JSON for Redis caching."""
    return json.dumps({
        "id": device.id,
        "factory_id": device.factory_id,
        "device_key": device.device_key,
        "name": device.name,
        "is_active": device.is_active
    })


def device_from_json(data: str) -> Device:
    """Deserialize Device from JSON."""
    obj = json.loads(data)
    device = Device(
        id=obj["id"],
        factory_id=obj["factory_id"],
        device_key=obj["device_key"],
        name=obj.get("name"),
        is_active=obj["is_active"]
    )
    return device


async def get_factory_by_slug(
    redis: Redis,
    db: AsyncSession,
    slug: str
) -> Optional[Factory]:
    """
    Get factory by slug with Redis caching (60-second TTL).
    
    Args:
        redis: Redis client
        db: Database session
        slug: Factory slug
    
    Returns:
        Factory object or None if not found
    """
    cache_key = f"factory:slug:{slug}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        logger.debug("factory.cache_hit", slug=slug)
        return factory_from_json(cached)
    
    # Cache miss - query database
    logger.debug("factory.cache_miss", slug=slug)
    result = await db.execute(
        select(Factory).where(Factory.slug == slug)
    )
    factory = result.scalar_one_or_none()
    
    # Cache the result (even if None, to prevent repeated DB queries)
    if factory:
        await redis.setex(cache_key, 60, factory_to_json(factory))
        logger.debug("factory.cached", slug=slug, factory_id=factory.id)
    
    return factory


async def get_or_create_device(
    redis: Redis,
    db: AsyncSession,
    factory_id: int,
    device_key: str
) -> Device:
    """
    Get or auto-create device with Redis caching (60-second TTL).
    Enables zero-config device onboarding.
    
    Args:
        redis: Redis client
        db: Database session
        factory_id: Factory ID
        device_key: Device key (e.g., "M01")
    
    Returns:
        Device object (existing or newly created)
    """
    cache_key = f"device:{factory_id}:{device_key}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(
            "device.cache_hit",
            factory_id=factory_id,
            device_key=device_key
        )
        return device_from_json(cached)
    
    # Cache miss - query database
    logger.debug(
        "device.cache_miss",
        factory_id=factory_id,
        device_key=device_key
    )
    result = await db.execute(
        select(Device).where(
            Device.factory_id == factory_id,
            Device.device_key == device_key
        )
    )
    device = result.scalar_one_or_none()
    
    # Auto-create if not found
    if not device:
        device = Device(
            factory_id=factory_id,
            device_key=device_key,
            name=None,
            is_active=True,
            last_seen=datetime.utcnow()
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        logger.info(
            "device.auto_registered",
            factory_id=factory_id,
            device_key=device_key,
            device_id=device.id
        )
    
    # Cache the device
    await redis.setex(cache_key, 60, device_to_json(device))
    logger.debug(
        "device.cached",
        factory_id=factory_id,
        device_key=device_key,
        device_id=device.id
    )
    
    return device
