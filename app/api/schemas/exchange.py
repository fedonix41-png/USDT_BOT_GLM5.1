"""Exchange schemas for API."""

from decimal import Decimal

from pydantic import BaseModel, Field


class ExchangeSettingsResponse(BaseModel):
    buy_rate: Decimal | None
    sell_rate: Decimal | None
    buy_enabled: bool
    sell_enabled: bool
    bot_enabled: bool
    requisites_card: str
    requisites_wallet: str
    notification_chats: list[str]


class ExchangeSettingsUpdateRequest(BaseModel):
    buy_rate: Decimal | None = Field(None, description="New buy rate (RUB per USDT)")
    sell_rate: Decimal | None = Field(None, description="New sell rate (RUB per USDT)")
    buy_enabled: bool | None = Field(None, description="Enable/disable buying")
    sell_enabled: bool | None = Field(None, description="Enable/disable selling")
    bot_enabled: bool | None = Field(None, description="Enable/disable bot for clients")
    requisites_card: str | None = Field(None, description="Card requisites for payments")
    requisites_wallet: str | None = Field(None, description="USDT wallet address for payments")
    notification_chats: list[str] | None = Field(None, description="List of notification chat IDs")
