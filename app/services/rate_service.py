"""Rate service — current rates, history, rate changes."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.rate import Rate, RateTypeEnum
from app.repositories.audit_repo import AuditRepository
from app.repositories.rate_repo import RateRepository


class RateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rate_repo = RateRepository(session)
        self.audit_repo = AuditRepository(session)

    async def get_current_rate(self, rate_type: RateTypeEnum) -> Decimal | None:
        rate = await self.rate_repo.get_current_rate(rate_type)
        return rate.value if rate else None

    async def set_rate(self, rate_type: RateTypeEnum, value: Decimal, set_by_user_id: int) -> Rate:
        rate = await self.rate_repo.create(
            rate_type=rate_type,
            value=value,
            set_by=set_by_user_id,
        )
        await self.audit_repo.log(
            user_id=set_by_user_id,
            action=f"change_rate_{rate_type.value}",
            details={"new_value": str(value), "rate_type": rate_type.value},
        )
        return rate

    async def get_rate_history(self, rate_type: RateTypeEnum, limit: int = 10) -> list[Rate]:
        return await self.rate_repo.get_rate_history(rate_type, limit)
