"""JWT utilities for authentication."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import settings


def generate_access_token(user_id: int, role: str) -> tuple[str, str, int]:
    jti = secrets.token_urlsafe(16)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.API_ACCESS_TOKEN_EXPIRE)

    payload: dict[str, Any] = {
        "sub": f"user_id:{user_id}",
        "role": role,
        "exp": expires_at,
        "iat": now,
        "jti": jti,
        "type": "access",
    }

    token = jwt.encode(payload, settings.API_SECRET_KEY, algorithm="HS256")
    return token, jti, settings.API_ACCESS_TOKEN_EXPIRE


def generate_refresh_token() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(32)
    jti = secrets.token_urlsafe(16)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, jti, token_hash


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.API_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_access_token(token: str) -> dict[str, Any] | None:
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_user_id_from_payload(payload: dict[str, Any]) -> int | None:
    sub = payload.get("sub", "")
    if sub.startswith("user_id:"):
        try:
            return int(sub.split(":")[1])
        except (ValueError, IndexError):
            return None
    return None
