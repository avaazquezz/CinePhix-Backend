"""
Redis-backed sliding-window rate limiter.

Usage:
    from app.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

Environment variables (via app.config):
    RATE_LIMIT_ENABLED  — "true" (default) or "false"
    RATE_LIMIT_DEFAULT — "100/minute" (per-IP global limit)
"""

import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.redis import get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter per IP address.

    Endpoints can override the default limit via decorator or route config:
        @router.post("/ai/chat", config={"rate_limit": "20/minute"})
    """

    # Default limits: endpoint → limit string
    DEFAULT_LIMITS = {
        "POST:/auth/register": "5/minute",
        "POST:/auth/login": "10/minute",
        "POST:/reviews": "10/minute",
        "POST:/ai/chat": "20/minute",
        "_default": "100/minute",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip if rate limiting is disabled
        from app.config import settings

        if not getattr(settings, "rate_limit_enabled", True):
            return await call_next(request)

        # Build the key: "rl:<ip>:<method>:<path>"
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Check route-specific limit first
        route_key = f"{method}:{path}"
        limit_str = self.DEFAULT_LIMITS.get(route_key, self.DEFAULT_LIMITS["_default"])

        if not await self._check_rate_limit(client_ip, route_key, limit_str):
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        return response

    async def _check_rate_limit(self, ip: str, route: str, limit_str: str) -> bool:
        """
        Sliding window using Redis sorted sets.
        Returns True if request is allowed, False if over limit.
        """
        limit_str = limit_str.strip()
        if "/" not in limit_str:
            return True  # malformed, allow

        count_str, window_str = limit_str.split("/", 1)
        try:
            limit_count = int(count_str)
            window_seconds = self._window_to_seconds(window_str)
        except (ValueError, TypeError):
            return True  # malformed, allow

        redis_client = await get_redis()
        try:
            key = f"rl:{ip}:{route}"
            now = time.time()
            window_start = now - window_seconds

            # Remove old entries outside the window
            await redis_client.zremrangebyscore(key, 0, window_start)

            # Count current entries
            current = await redis_client.zcard(key)
            if current >= limit_count:
                return False

            # Add this request
            await redis_client.zadd(key, {str(now): now})
            await redis_client.expire(key, window_seconds + 1)
            return True
        finally:
            await redis_client.aclose()

    def _window_to_seconds(self, window: str) -> int:
        """Convert '1/minute', '5/hour', '1/day' to seconds."""
        window = window.strip().lower()
        mapping = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        for unit, multiplier in mapping.items():
            if window.endswith(unit):
                try:
                    return int(window.replace(unit, "").strip()) * multiplier
                except ValueError:
                    pass
        return 60  # default 1 minute
