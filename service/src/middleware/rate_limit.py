"""Rate limiting configuration using slowapi (Redis-backed) + global middleware."""

import redis.asyncio as aioredis
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
        headers={"Retry-After": str(exc.retry_after)},
    )


_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """IP-based rate limiter for all endpoints, backed by Redis.

    Applies a default 30 requests/minute per IP using a Redis sliding window.
    Endpoints with their own @limiter.limit() decorator have stricter limits
    and hit those first.
    """

    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.window = 60  # seconds

    def _get_client_ip(self, request: Request) -> str:
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next):
        # Skip health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        ip = self._get_client_ip(request)
        key = f"rl:global:{ip}"

        r = await _get_redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, self.window)

        if count > self.rpm:
            ttl = await r.ttl(key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(max(ttl, 1))},
            )

        return await call_next(request)
