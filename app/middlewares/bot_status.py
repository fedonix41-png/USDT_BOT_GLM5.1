"""Middleware for checking bot_enabled flag — blocks client access when bot is disabled."""

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings
from app.database.models.user import RoleEnum, User

logger = logging.getLogger(__name__)

_bot_enabled_cache: dict[str, Any] = {"value": True, "timestamp": 0.0}


class BotStatusMiddleware(BaseMiddleware):
    """Blocks client actions when bot is disabled (bot_enabled=0).

    Operators and admins always pass through.
    Uses a 30-second in-memory cache to reduce DB load.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")
        user: User | None = data.get("user")

        if user is None:
            return await handler(event, data)

        if user.role in (RoleEnum.super_admin, RoleEnum.admin, RoleEnum.operator):
            return await handler(event, data)

        now = time.monotonic()
        cache_age = now - _bot_enabled_cache["timestamp"]

        if cache_age > 30:
            try:
                result = await session.get(GlobalSettings, "bot_enabled")
                value = result.value if result else "1"
                _bot_enabled_cache["value"] = value == "1"
                _bot_enabled_cache["timestamp"] = now
            except Exception as e:
                logger.error(f"Error checking bot status: {e}")
                _bot_enabled_cache["value"] = True

        if not _bot_enabled_cache["value"]:
            if isinstance(event, CallbackQuery):
                await event.answer("Бот временно недоступен.", show_alert=True)
                return
            elif isinstance(event, Message):
                await event.answer("Бот временно недоступен.")
                return

        return await handler(event, data)
