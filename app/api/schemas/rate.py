"""Rate schemas for API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.database.models.rate import RateTypeEnum


class RateResponse(BaseModel):
    rate_type: RateTypeEnum
    value: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class CurrentRatesResponse(BaseModel):
    buy: Decimal | None
    sell: Decimal | None


class RateCreateRequest(BaseModel):
    rate_type: RateTypeEnum = Field(..., description="Type of rate (buy or sell)")
    value: Decimal = Field(..., gt=0, description="Rate value in RUB per USDT")


class RateHistoryResponse(BaseModel):
    items: list[RateResponse]
    total: int
