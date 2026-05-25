"""API middleware: rate limiting, IP whitelist, CORS."""

import logging
import time
from collections.abc import Awaitable, Callable

from aiohttp import web

from app.api.exceptions import LoginBlockedError, RateLimitError
from app.config import settings
from app.database.models.user import RoleEnum
from app.utils.redis import get_redis

logger = logging.getLogger(__name__)


async def rate_limit_middleware(
    app: web.Application, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def middleware_handler(request: web.Request) -> web.Response:
        if request.path.startswith("/api/v1/auth"):
            return await handler(request)

        if request.path == "/api/v1/health":
            return await handler(request)

        client_ip = request.remote or "unknown"
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

        return await handler(request)

    return middleware_handler


async def login_rate_limit_middleware(
    app: web.Application, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def middleware_handler(request: web.Request) -> web.Response:
        if request.path != "/api/v1/auth/login":
            return await handler(request)

        client_ip = request.remote or "unknown"
        block_key = f"login_blocked:{client_ip}"

        redis = await get_redis()

        blocked = await redis.get(block_key)
        if blocked:
            ttl = await redis.ttl(block_key)
            raise LoginBlockedError(retry_after=max(ttl, 1))

        return await handler(request)

    return middleware_handler


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


async def ip_whitelist_middleware(
    app: web.Application, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    from app.api.deps import check_ip_whitelist, get_current_user

    async def middleware_handler(request: web.Request) -> web.Response:
        if not settings.API_ADMIN_IP_WHITELIST:
            return await handler(request)

        admin_paths = [
            "/api/v1/users",
            "/api/v1/rates",
            "/api/v1/settings",
        ]

        is_admin_path = any(request.path.startswith(path) for path in admin_paths)
        if not is_admin_path:
            return await handler(request)

        try:
            user = await get_current_user(request)
            if user.role in (RoleEnum.admin, RoleEnum.super_admin):
                check_ip_whitelist(request)
        except Exception:
            pass

        return await handler(request)

    return middleware_handler


@web.middleware
async def cors_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> web.Response:
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)

    origin = request.headers.get("Origin", "")
    if settings.API_CORS_ORIGINS and origin in settings.API_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    elif not settings.API_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Max-Age"] = "86400"

    return response


@web.middleware
async def logging_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> web.Response:
    start_time = time.time()

    request_body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            request_body = await request.text()
            request["body_text"] = request_body
        except Exception:
            pass

    response = await handler(request)

    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.path} -> {response.status} ({duration:.3f}s)",
        extra={
            "method": request.method,
            "path": request.path,
            "status": response.status,
            "duration": duration,
            "client_ip": request.remote,
        },
    )

    return response
