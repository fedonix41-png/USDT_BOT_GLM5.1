"""Dependencies for API handlers."""

import ipaddress
import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.api.auth import decode_token, get_user_id_from_payload
from app.api.exceptions import ForbiddenError, UnauthorizedError
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum, User
from app.repositories.user_repo import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    payload = decode_token(token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    user_id = get_user_id_from_payload(payload)
    if user_id is None:
        raise UnauthorizedError("Invalid token payload")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User not found")
    if user.is_blocked:
        raise ForbiddenError("User is blocked")
        
    # Optional: store in request state if needed
    request.state.user = user
    return user


async def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return user.id


def require_role(*roles: RoleEnum):
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"Role {user.role.value} is not allowed")
        return user

    return role_checker


def require_min_role(min_role: RoleEnum):
    role_levels = {
        RoleEnum.client: 1,
        RoleEnum.operator: 2,
        RoleEnum.admin: 3,
        RoleEnum.super_admin: 4,
    }

    def role_checker(user: User = Depends(get_current_user)) -> User:
        user_level = role_levels.get(user.role, 0)
        min_level = role_levels.get(min_role, 0)
        if user_level < min_level:
            raise ForbiddenError(f"Role {user.role.value} is not allowed for this action")
        return user

    return role_checker


def check_ip_whitelist(request: Request):
    if not settings.API_ADMIN_IP_WHITELIST:
        return

    client_ip = request.client.host if request.client else None
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


def require_admin_ip(request: Request, user: User = Depends(get_current_user)) -> User:
    if user.role in (RoleEnum.admin, RoleEnum.super_admin):
        check_ip_whitelist(request)
    return user
