"""User repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self, telegram_id: int, username: str | None, full_name: str | None, default_role: RoleEnum = RoleEnum.client
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            return user
        return await self.create(
            telegram_id=telegram_id, username=username, full_name=full_name, role=default_role
        )

    async def set_role(self, user_id: int, role: RoleEnum) -> User | None:
        return await self.update(user_id, role=role)

    async def set_blocked(self, user_id: int, is_blocked: bool) -> User | None:
        return await self.update(user_id, is_blocked=is_blocked)

    async def set_phone(self, user_id: int, phone: str) -> User | None:
        return await self.update(user_id, phone=phone)
