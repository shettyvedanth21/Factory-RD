from typing import AsyncGenerator

from redis import asyncio as aioredis
from redis.asyncio import Redis

from .config import settings


# Redis client instance
_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """
    Get or create the Redis client instance.
    
    Returns:
        Redis client
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    return _redis_client


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI dependency for Redis client.
    
    Usage:
        @app.get("/items")
        async def get_items(redis: Redis = Depends(get_redis)):
            await redis.set("key", "value")
    """
    client = await get_redis_client()
    try:
        yield client
    finally:
        # Don't close the client - it's reused
        pass


async def check_redis_health() -> bool:
    """
    Check Redis connectivity.
    
    Returns:
        True if Redis is accessible, False otherwise
    """
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception:
        return False


async def close_redis():
    """Close the Redis connection (call on shutdown)."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
