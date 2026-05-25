"""Order schemas for API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.database.models.order import OrderStatusEnum, OrderTypeEnum


class OrderResponse(BaseModel):
    id: int
    user_id: int
    order_type: OrderTypeEnum
    amount_usdt: Decimal
    rate: Decimal
    total_fiat: Decimal
    status: OrderStatusEnum
    link_broken: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    offset: int
    limit: int


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatusEnum = Field(..., description="New status (completed or cancelled)")

    model_config = {"from_attributes": True}
