"""Redis client for telemetry service."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from redis import asyncio as aioredis
from redis.asyncio import Redis

from config import settings


@asynccontextmanager
async def get_redis_client() -> AsyncGenerator[Redis, None]:
    """
    Get a Redis client for the telemetry service.
    
    Usage:
        async with get_redis_client() as redis:
            # Use redis
    """
    client = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    try:
        yield client
    finally:
        await client.close()
