"""Dependencies for API handlers."""

import ipaddress
import logging
from collections.abc import Awaitable, Callable

from aiohttp import web

from app.api.auth import decode_token, get_user_id_from_payload
from app.api.exceptions import ForbiddenError, UnauthorizedError
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum, User
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


async def get_session():
    async with async_session_maker() as session:
        yield session


async def get_current_user(request: web.Request) -> User:
    user = request.get("user")
    if user is None:
        raise UnauthorizedError("User not authenticated")
    return user


async def get_current_user_id(request: web.Request) -> int:
    user = await get_current_user(request)
    return user.id


def require_role(*roles: RoleEnum) -> Callable[[web.Request, User], Awaitable[None]]:
    async def role_checker(request: web.Request) -> None:
        user = await get_current_user(request)
        if user.role not in roles:
            raise ForbiddenError(f"Role {user.role.value} is not allowed")

    return role_checker


def require_min_role(min_role: RoleEnum) -> Callable[[web.Request], Awaitable[None]]:
    role_levels = {
        RoleEnum.client: 1,
        RoleEnum.operator: 2,
        RoleEnum.admin: 3,
        RoleEnum.super_admin: 4,
    }

    async def role_checker(request: web.Request) -> None:
        user = await get_current_user(request)
        user_level = role_levels.get(user.role, 0)
        min_level = role_levels.get(min_role, 0)
        if user_level < min_level:
            raise ForbiddenError(f"Role {user.role.value} is not allowed for this action")

    return role_checker


def check_ip_whitelist(request: web.Request) -> None:
    if not settings.API_ADMIN_IP_WHITELIST:
        return

    client_ip = request.remote
    if client_ip is None:
        raise ForbiddenError("Cannot determine client IP")

    try:
        ip = ipaddress.ip_address(client_ip)
        for allowed in settings.API_ADMIN_IP_WHITELIST:
            if "/" in allowed:
                if ip in ipaddress.ip_network(allowed, strict=False):
                    return
            else:
                if ip == ipaddress.ip_address(allowed):
                    return
        raise ForbiddenError("IP address not in whitelist")
    except ValueError:
        raise ForbiddenError("Invalid IP address")


async def auth_middleware(
    app: web.Application, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def middleware_handler(request: web.Request) -> web.Response:
        if request.path.startswith("/api/v1/auth"):
            return await handler(request)

        if request.path == "/api/v1/health":
            return await handler(request)

        if request.method == "GET" and request.path == "/api/v1/rates":
            return await handler(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise UnauthorizedError("Missing or invalid Authorization header")

        token = auth_header[7:]
        payload = decode_token(token)
        if payload is None:
            raise UnauthorizedError("Invalid or expired token")

        user_id = get_user_id_from_payload(payload)
        if user_id is None:
            raise UnauthorizedError("Invalid token payload")

        async with async_session_maker() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if user is None:
                raise UnauthorizedError("User not found")
            if user.is_blocked:
                raise ForbiddenError("User is blocked")
            request["user"] = user
            request["token_payload"] = payload

        return await handler(request)

    return middleware_handler
