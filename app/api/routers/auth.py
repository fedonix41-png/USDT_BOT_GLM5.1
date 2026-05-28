"""Auth router for API."""

import json
import logging
from datetime import UTC, datetime, timedelta

from aiohttp import web
from pydantic import ValidationError

from app.api.auth import generate_access_token, generate_refresh_token, hash_token
from app.api.deps import get_current_user
from app.api.exceptions import ForbiddenError, UnauthorizedError
from app.api.exceptions import ValidationError as APIValidationError
from app.api.middleware import record_login_attempt
from app.api.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum
from app.repositories.api_token_repo import APITokenRepository
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


@router.post("/api/v1/auth/login")
async def login(request: web.Request) -> web.Response:
    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        login_data = LoginRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    client_ip = request.remote or "unknown"

    if login_data.api_key != settings.API_SECRET_KEY:
        await record_login_attempt(client_ip, success=False)
        raise UnauthorizedError("Invalid API key")

    async with async_session_maker() as session:
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

        return web.json_response(response_data.model_dump(mode='json'))


@router.post("/api/v1/auth/refresh")
async def refresh(request: web.Request) -> web.Response:
    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        refresh_data = RefreshRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    token_hash = hash_token(refresh_data.refresh_token)

    async with async_session_maker() as session:
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

        return web.json_response(response_data.model_dump(mode='json'))


@router.post("/api/v1/auth/logout")
async def logout(request: web.Request) -> web.Response:
    user = await get_current_user(request)

    async with async_session_maker() as session:
        token_repo = APITokenRepository(session)
        revoked_count = await token_repo.revoke_all_for_user(user.id)

    logger.info(f"User {user.telegram_id} logged out, revoked {revoked_count} tokens")

    return web.json_response({"message": "Logged out successfully", "revoked_tokens": revoked_count})
