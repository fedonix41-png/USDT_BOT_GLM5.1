"""Global settings repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[GlobalSettings]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GlobalSettings, session)

    async def get(self, key: str) -> str | None:
        instance = await self.session.get(GlobalSettings, key)
        if instance is None:
            return None
        return instance.value

    async def set(self, key: str, value: str) -> GlobalSettings:
        instance = await self.session.get(GlobalSettings, key)
        if instance is None:
            return await self.create(key=key, value=value)
        instance.value = value
        await self.session.flush()
        return instance

    async def get_or_default(self, key: str, default: str) -> str:
        value = await self.get(key)
        return value if value is not None else default
