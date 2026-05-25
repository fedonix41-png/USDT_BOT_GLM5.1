"""User service — registration, role management."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models.user import RoleEnum, User
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)

    async def get_or_create(self, telegram_id: int, username: str | None, full_name: str | None) -> User:
        default_role = (
            RoleEnum.super_admin
            if telegram_id == settings.SUPER_ADMIN_TELEGRAM_ID
            else RoleEnum.client
        )
        user = await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            default_role=default_role,
        )
        if user.username != username or user.full_name != full_name:
            user.username = username
            user.full_name = full_name
            await self.session.flush()
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def set_role(self, user_id: int, role: RoleEnum, set_by_user_id: int) -> User | None:
        user = await self.user_repo.set_role(user_id, role)
        if user is not None:
            await self.audit_repo.log(
                user_id=set_by_user_id,
                action=f"assign_role_{role.value}",
                details={"target_user_id": user_id, "new_role": role.value},
            )
        return user

    async def is_super_admin(self, telegram_id: int) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return user is not None and user.role == RoleEnum.super_admin
