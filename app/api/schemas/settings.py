"""Settings schemas for API."""

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    bot_enabled: bool
    buy_enabled: bool
    sell_enabled: bool


class SettingsUpdateRequest(BaseModel):
    bot_enabled: bool | None = Field(None, description="Enable/disable bot for clients")
    buy_enabled: bool | None = Field(None, description="Enable/disable buying")
    sell_enabled: bool | None = Field(None, description="Enable/disable selling")
