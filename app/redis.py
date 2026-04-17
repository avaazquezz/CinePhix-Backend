"""Async Redis client for caching and rate limiting."""

from functools import lru_cache

import redis.asyncio as redis

from app.config import settings


@lru_cache
def get_redis_client() -> redis.Redis:
    """Return cached Redis client instance."""
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def get_redis() -> redis.Redis:
    """Dependency that provides a Redis client."""
    return get_redis_client()


async def close_redis() -> None:
    """Close Redis connection."""
    client = get_redis_client()
    await client.close()