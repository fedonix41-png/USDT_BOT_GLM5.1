"""Auth schemas for API."""

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    api_key: str = Field(..., description="API secret key from configuration")


class TelegramVerifyRequest(BaseModel):
    initData: str = Field(..., description="Telegram WebApp initData")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token: str | None = None
    user: dict[str, Any] | None = None
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
