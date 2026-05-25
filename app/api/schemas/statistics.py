"""Statistics schemas for API."""

from decimal import Decimal

from pydantic import BaseModel


class StatisticsResponse(BaseModel):
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    total_volume_usdt: Decimal
    total_volume_fiat: Decimal
    buy_orders: int
    sell_orders: int
