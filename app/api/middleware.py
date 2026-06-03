"""API middleware: rate limiting, IP whitelist, CORS."""

import logging
import time
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.exceptions import LoginBlockedError, RateLimitError
from app.config import settings
from app.utils.redis import get_redis

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path.startswith("/api/v1/auth"):
            return await call_next(request)
        if request.url.path == "/api/v1/health":
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"
        
        redis = await get_redis()
        current = await redis.get(key)
        
        if current is None:
            await redis.set(key, "1", ex=60)
        else:
            count = int(current)
            if count >= settings.API_RATE_LIMIT:
                raise RateLimitError(f"Rate limit exceeded. Max {settings.API_RATE_LIMIT} requests per minute.")
            await redis.incr(key)
            
        return await call_next(request)

class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path != "/api/v1/auth/login":
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        block_key = f"login_blocked:{client_ip}"
        
        redis = await get_redis()
        blocked = await redis.get(block_key)
        
        if blocked:
            ttl = await redis.ttl(block_key)
            raise LoginBlockedError(retry_after=max(ttl, 1))
            
        return await call_next(request)

async def record_login_attempt(client_ip: str, success: bool) -> None:
    redis = await get_redis()
    key = f"login_attempts:{client_ip}"
    block_key = f"login_blocked:{client_ip}"

    if success:
        await redis.delete(key)
    else:
        current = await redis.get(key)
        attempts = int(current) + 1 if current else 1
        await redis.set(key, str(attempts), ex=settings.API_LOGIN_BLOCK_DURATION)

        if attempts >= 5:
            await redis.set(block_key, "1", ex=settings.API_LOGIN_BLOCK_DURATION)
            await redis.delete(key)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration": duration,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response
