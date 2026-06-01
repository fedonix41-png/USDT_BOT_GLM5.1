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
    rejection_reason: str | None = None
    payment_link_snapshot: str | None = None
    is_paid_from_balance: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        instance = super().model_validate(obj, *args, **kwargs)
        if hasattr(obj, "payment_link_snapshot") and obj.payment_link_snapshot:
            try:
                from app.config import settings
                from app.services.encryption import EncryptionService
                enc = EncryptionService(settings.ENCRYPTION_KEY)
                decrypted = enc.decrypt(obj.payment_link_snapshot)
                if decrypted and decrypted.startswith("[BALANCE_PAID]"):
                    instance.is_paid_from_balance = True
                    instance.payment_link_snapshot = decrypted.replace("[BALANCE_PAID]", "", 1)
                else:
                    instance.payment_link_snapshot = decrypted
            except Exception:
                instance.payment_link_snapshot = obj.payment_link_snapshot
        return instance


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    offset: int
    limit: int


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatusEnum = Field(..., description="New status (completed or cancelled)")
    rejection_reason: str | None = Field(None, description="Reason for rejection (if cancelling)")

    model_config = {"from_attributes": True}


class OrderCreateRequest(BaseModel):
    order_type: OrderTypeEnum = Field(..., description="Order type: buy or sell")
    amount_usdt: Decimal = Field(..., gt=0, description="Amount of USDT")
    client_details: str = Field(..., description="Payment details from client")
