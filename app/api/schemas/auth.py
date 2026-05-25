"""Auth schemas for API."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    api_key: str = Field(..., description="API secret key from configuration")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
