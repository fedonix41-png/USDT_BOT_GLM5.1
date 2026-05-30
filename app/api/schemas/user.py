"""User schemas for API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.database.models.user import RoleEnum


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    role: RoleEnum
    is_blocked: bool
    balance: Decimal = Decimal("0.00")
    fiat_balance: Decimal = Decimal("0.00")
    referrals_count: int = 0
    referral_earned: Decimal = Decimal("0.00")
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int


class RoleUpdateRequest(BaseModel):
    role: RoleEnum = Field(..., description="New role for the user")
