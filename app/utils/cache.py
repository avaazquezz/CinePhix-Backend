"""Redis caching utilities."""

import json
from functools import wraps
from typing import Any, Callable

import redis.asyncio as redis

from app.config import settings


async def get_cached(key: str) -> Any | None:
    """Get a value from Redis cache."""
    client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    finally:
        await client.aclose()


async def set_cached(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Set a value in Redis cache with TTL."""
    client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        await client.setex(key, ttl_seconds, json.dumps(value))
    finally:
        await client.aclose()


async def delete_cached(key: str) -> None:
    """Delete a key from Redis cache."""
    client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        await client.delete(key)
    finally:
        await client.aclose()


async def invalidate_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern."""
    client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
    finally:
        await client.aclose()


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    parts = [str(arg) for arg in args]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)


# Cache TTL constants (in seconds)
TMDB_MOVIE_TTL = 3600  # 1 hour
TMDB_TRENDING_TTL = 900  # 15 minutes
TMDB_SEARCH_TTL = 300  # 5 minutes
USER_SESSION_TTL = 604800  # 7 days