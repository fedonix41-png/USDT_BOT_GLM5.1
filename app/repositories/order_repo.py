"""Order repository."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import Order, OrderStatusEnum, OrderTypeEnum
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Order, session)

    async def get_active_orders(self, offset: int = 0, limit: int = 5) -> list[Order]:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        stmt = (
            select(Order)
            .where(Order.status == OrderStatusEnum.created, Order.created_at >= cutoff)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_orders(self) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        stmt = select(func.count()).where(
            Order.status == OrderStatusEnum.created, Order.created_at >= cutoff
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_broken_link_orders(self, order_type: OrderTypeEnum | None = None) -> list[Order]:
        stmt = select(Order).where(
            Order.link_broken == True,  # noqa: E712
            Order.status == OrderStatusEnum.created,
        )
        if order_type is not None:
            stmt = stmt.where(Order.order_type == order_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_orders(self, user_id: int, offset: int = 0, limit: int = 10) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_orders(self, user_id: int) -> int:
        stmt = select(func.count()).where(Order.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_statistics(self, start: datetime, end: datetime) -> dict:
        base_filter = Order.created_at.between(start, end)
        active_statuses = [OrderStatusEnum.created, OrderStatusEnum.completed]

        buy_stmt = select(
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.amount_usdt), 0).label("total_usdt"),
        ).where(base_filter, Order.order_type == OrderTypeEnum.buy, Order.status.in_(active_statuses))
        sell_stmt = select(
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.amount_usdt), 0).label("total_usdt"),
        ).where(base_filter, Order.order_type == OrderTypeEnum.sell, Order.status.in_(active_statuses))
        total_stmt = select(
            func.count(Order.id).label("count"),
        ).where(base_filter, Order.status.in_(active_statuses))

        buy_result = (await self.session.execute(buy_stmt)).one()
        sell_result = (await self.session.execute(sell_stmt)).one()
        total_result = (await self.session.execute(total_stmt)).one()

        return {
            "count_buy": buy_result.count,
            "sum_buy": float(buy_result.total_usdt),
            "count_sell": sell_result.count,
            "sum_sell": float(sell_result.total_usdt),
            "total": total_result.count,
        }
