"""Settings service — bot flags, payment links (encrypted)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import OrderTypeEnum
from app.repositories.audit_repo import AuditRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.encryption import EncryptionService

_DEFAULTS = {
    "bot_enabled": "1",
    "buy_enabled": "1",
    "sell_enabled": "1",
    "payment_link_buy": "",
    "payment_link_sell": "",
}

_LINK_KEYS = {
    OrderTypeEnum.buy: "payment_link_buy",
    OrderTypeEnum.sell: "payment_link_sell",
}


class SettingsService:
    def __init__(self, session: AsyncSession, encryption: EncryptionService) -> None:
        self.session = session
        self.settings_repo = SettingsRepository(session)
        self.audit_repo = AuditRepository(session)
        self.encryption = encryption

    async def get(self, key: str) -> str | None:
        return await self.settings_repo.get(key)

    async def set(self, key: str, value: str, user_id: int | None = None) -> None:
        await self.settings_repo.set(key, value)
        if user_id is not None:
            await self.audit_repo.log(
                user_id=user_id,
                action=f"change_setting_{key}",
                details={"key": key, "value": "***" if "link" in key else value},
            )

    async def _get_flag(self, key: str) -> bool:
        value = await self.settings_repo.get_or_default(key, _DEFAULTS[key])
        return value == "1"

    async def is_bot_enabled(self) -> bool:
        return await self._get_flag("bot_enabled")

    async def is_buy_enabled(self) -> bool:
        return await self._get_flag("buy_enabled")

    async def is_sell_enabled(self) -> bool:
        return await self._get_flag("sell_enabled")

    async def get_payment_link(self, order_type: OrderTypeEnum) -> str:
        key = _LINK_KEYS[order_type]
        encrypted = await self.settings_repo.get_or_default(key, _DEFAULTS[key])
        if not encrypted:
            return ""
        return self.encryption.decrypt(encrypted)

    async def set_payment_link(self, order_type: OrderTypeEnum, link: str, user_id: int) -> None:
        key = _LINK_KEYS[order_type]
        encrypted = self.encryption.encrypt(link) if link else ""
        await self.set(key, encrypted, user_id=user_id)

    async def toggle_flag(self, key: str, user_id: int) -> bool:
        current = await self.settings_repo.get_or_default(key, _DEFAULTS.get(key, "1"))
        new_value = "0" if current == "1" else "1"
        await self.set(key, new_value, user_id=user_id)
        return new_value == "1"
