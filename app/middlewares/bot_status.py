"""Middleware for checking bot_enabled flag — blocks client access when bot is disabled."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings
from app.database.models.user import RoleEnum, User
from app.utils.redis import get_cached_flag, set_cached_flag

logger = logging.getLogger(__name__)

CACHE_TTL = 30


class BotStatusMiddleware(BaseMiddleware):
    """Blocks client actions when bot is disabled (bot_enabled=0).

    Operators and admins always pass through.
    Uses Redis cache with TTL to reduce DB load and support multiple instances.
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

        try:
            cached = await get_cached_flag("bot_enabled", ttl=CACHE_TTL)
            if cached is not None:
                is_enabled = cached == "1"
            else:
                result = await session.get(GlobalSettings, "bot_enabled")
                value = result.value if result else "1"
                is_enabled = value == "1"
                await set_cached_flag("bot_enabled", value, ttl=CACHE_TTL)
        except Exception as e:
            logger.error(f"Error checking bot status: {e}")
            is_enabled = True

        if not is_enabled:
            if isinstance(event, CallbackQuery):
                await event.answer("Бот временно недоступен.", show_alert=True)
                return
            elif isinstance(event, Message):
                await event.answer("Бот временно недоступен.")
                return

        return await handler(event, data)
