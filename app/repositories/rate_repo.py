"""Rate repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.rate import Rate, RateTypeEnum
from app.repositories.base import BaseRepository


class RateRepository(BaseRepository[Rate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Rate, session)

    async def get_current_rate(self, rate_type: RateTypeEnum) -> Rate | None:
        stmt = (
            select(Rate)
            .where(Rate.rate_type == rate_type)
            .order_by(Rate.created_at.desc(), Rate.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rate_history(self, rate_type: RateTypeEnum, limit: int = 10) -> list[Rate]:
        stmt = (
            select(Rate)
            .where(Rate.rate_type == rate_type)
            .order_by(Rate.created_at.desc(), Rate.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
