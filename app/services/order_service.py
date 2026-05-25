"""Order service — create, cancel, complete, statistics."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import Order, OrderStatusEnum, OrderTypeEnum
from app.repositories.audit_repo import AuditRepository
from app.repositories.order_repo import OrderRepository
from app.services.encryption import EncryptionService


class OrderService:
    def __init__(self, session: AsyncSession, encryption: EncryptionService) -> None:
        self.session = session
        self.order_repo = OrderRepository(session)
        self.audit_repo = AuditRepository(session)
        self.encryption = encryption

    async def create_order(
        self,
        user_id: int,
        order_type: OrderTypeEnum,
        amount_usdt: Decimal,
        rate: Decimal,
        payment_link: str,
        message_id: int,
        chat_id: int,
    ) -> Order:
        total_fiat = amount_usdt * rate
        encrypted_link = self.encryption.encrypt(payment_link) if payment_link else None
        order = await self.order_repo.create(
            user_id=user_id,
            order_type=order_type,
            amount_usdt=amount_usdt,
            rate=rate,
            total_fiat=total_fiat,
            payment_link_snapshot=encrypted_link,
            message_id=message_id,
            chat_id=chat_id,
        )
        return order

    async def cancel_order(self, order_id: int, user_id: int) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if order is None or order.status != OrderStatusEnum.created:
            return None
        order.status = OrderStatusEnum.cancelled
        await self.session.flush()
        return order

    async def complete_order(self, order_id: int, operator_user_id: int) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if order is None or order.status != OrderStatusEnum.created:
            return None
        order.status = OrderStatusEnum.completed
        await self.session.flush()
        await self.audit_repo.log(
            user_id=operator_user_id,
            action="complete_order",
            details={"order_id": order_id, "order_type": order.order_type.value},
        )
        return order

    async def mark_link_broken(self, order_id: int) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            return None
        order.link_broken = True
        await self.session.flush()
        return order

    async def get_active_orders(self, offset: int = 0, limit: int = 5) -> list[Order]:
        return await self.order_repo.get_active_orders(offset, limit)

    async def count_active_orders(self) -> int:
        return await self.order_repo.count_active_orders()

    async def get_broken_link_orders(self, order_type: OrderTypeEnum | None = None) -> list[Order]:
        return await self.order_repo.get_broken_link_orders(order_type)

    async def get_statistics(self, start: datetime, end: datetime) -> dict:
        return await self.order_repo.get_statistics(start, end)

    async def get_order_by_id(self, order_id: int) -> Order | None:
        return await self.order_repo.get_by_id(order_id)

    async def update_order_message(self, order_id: int, message_id: int, chat_id: int) -> Order | None:
        return await self.order_repo.update(order_id, message_id=message_id, chat_id=chat_id)
