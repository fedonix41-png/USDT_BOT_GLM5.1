"""Redis utilities for caching and coordination."""

import logging

from redis.asyncio import ConnectionPool, Redis

from app.config import settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool (singleton)."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


async def get_redis() -> Redis:
    """Get Redis client from the pool."""
    return Redis(connection_pool=get_redis_pool())


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection pool closed")


async def get_cached_flag(key: str, ttl: int = 30) -> str | None:
    """Get cached flag value from Redis.

    Args:
        key: Cache key (e.g., 'bot_enabled', 'buy_enabled').
        ttl: Time-to-live in seconds for cache refresh.

    Returns:
        Cached value or None if not cached.
    """
    redis = await get_redis()
    return await redis.get(key)


async def set_cached_flag(key: str, value: str, ttl: int = 30) -> None:
    """Set cached flag value in Redis.

    Args:
        key: Cache key.
        value: Value to cache.
        ttl: Time-to-live in seconds.
    """
    redis = await get_redis()
    await redis.set(key, value, ex=ttl)
