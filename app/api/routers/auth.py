"""Auth router for API."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import generate_access_token, generate_refresh_token, hash_token
from app.api.deps import get_current_user, get_session
from app.api.exceptions import ForbiddenError, UnauthorizedError
from app.api.middleware import record_login_attempt
from app.api.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.config import settings
from app.database.models.user import RoleEnum, User
from app.repositories.api_token_repo import APITokenRepository
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"

    if login_data.api_key != settings.API_SECRET_KEY:
        await record_login_attempt(client_ip, success=False)
        raise UnauthorizedError("Invalid API key")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(login_data.telegram_id)

    if user is None:
        await record_login_attempt(client_ip, success=False)
        raise UnauthorizedError("User not found")

    if user.role == RoleEnum.client:
        await record_login_attempt(client_ip, success=False)
        raise ForbiddenError("API access not allowed for clients")

    if user.is_blocked:
        await record_login_attempt(client_ip, success=False)
        raise ForbiddenError("User is blocked")

    token_repo = APITokenRepository(session)

    access_token, access_jti, expires_in = generate_access_token(user.id, user.role.value)
    refresh_token, refresh_jti, refresh_hash = generate_refresh_token()

    expires_at = datetime.now(UTC) + timedelta(seconds=settings.API_REFRESH_TOKEN_EXPIRE)
    await token_repo.create_token(
        user_id=user.id,
        token_hash=refresh_hash,
        jti=refresh_jti,
        expires_at=expires_at,
    )

    await record_login_attempt(client_ip, success=True)

    response_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )

    logger.info(f"User {user.telegram_id} logged in from IP {client_ip}")

    return response_data


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    refresh_data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    token_hash = hash_token(refresh_data.refresh_token)
    token_repo = APITokenRepository(session)

    tokens = await token_repo.get_all()
    stored_token = None
    for t in tokens:
        if t.token_hash == token_hash and not t.revoked:
            stored_token = t
            break

    if stored_token is None:
        raise UnauthorizedError("Invalid refresh token")

    if stored_token.expires_at < datetime.now(UTC):
        await token_repo.revoke(stored_token.jti)
        raise UnauthorizedError("Refresh token expired")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(stored_token.user_id)

    if user is None or user.is_blocked:
        await token_repo.revoke(stored_token.jti)
        raise UnauthorizedError("User not found or blocked")

    await token_repo.revoke(stored_token.jti)

    access_token, access_jti, expires_in = generate_access_token(user.id, user.role.value)
    new_refresh_token, new_refresh_jti, new_refresh_hash = generate_refresh_token()

    expires_at = datetime.now(UTC) + timedelta(seconds=settings.API_REFRESH_TOKEN_EXPIRE)
    await token_repo.create_token(
        user_id=user.id,
        token_hash=new_refresh_hash,
        jti=new_refresh_jti,
        expires_at=expires_at,
    )

    response_data = TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
    )

    return response_data


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    token_repo = APITokenRepository(session)
    revoked_count = await token_repo.revoke_all_for_user(user.id)

    logger.info(f"User {user.telegram_id} logged out, revoked {revoked_count} tokens")

    return {"message": "Logged out successfully", "revoked_tokens": revoked_count}
