"""Throttling middleware to prevent spam."""

import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Rate limiting middleware to prevent spam using Redis.
    
    Limits:
    - Commands: 1 message per second
    - FSM input: 5 messages per minute
    - Regular messages: 3 messages per second
    """

    COMMAND_LIMIT = 1.0
    FSM_LIMIT = 5
    FSM_WINDOW = 60.0
    REGULAR_LIMIT = 3.0

    def __init__(self) -> None:
        pass

    def _get_user_id(self, event: TelegramObject) -> int | None:
        if hasattr(event, "from_user") and event.from_user:
            return event.from_user.id
        if hasattr(event, "message") and hasattr(event.message, "from_user"):
            return event.message.from_user.id
        return None

    def _is_command(self, event: TelegramObject) -> bool:
        if hasattr(event, "text") and event.text:
            return event.text.startswith("/")
        if hasattr(event, "message") and hasattr(event.message, "text"):
            text = event.message.text
            return text and text.startswith("/")
        return False

    async def _check_command_throttle(self, user_id: int) -> bool:
        try:
            from app.utils.redis import get_redis
            redis = await get_redis()
            key = f"throttle:cmd:{user_id}"
            # px expects milliseconds
            is_set = await redis.set(key, "1", px=int(self.COMMAND_LIMIT * 1000), nx=True)
            return bool(is_set)
        except Exception as e:
            logger.error("Redis throttle error (cmd): %s", e)
            return True  # Fail-open if Redis is down

    async def _check_fsm_throttle(self, user_id: int) -> bool:
        try:
            from app.utils.redis import get_redis
            redis = await get_redis()
            key = f"throttle:fsm:{user_id}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, int(self.FSM_WINDOW))
            return count <= self.FSM_LIMIT
        except Exception as e:
            logger.error("Redis throttle error (fsm): %s", e)
            return True

    async def _check_regular_throttle(self, user_id: int) -> bool:
        try:
            from app.utils.redis import get_redis
            redis = await get_redis()
            key = f"throttle:reg:{user_id}"
            is_set = await redis.set(key, "1", px=int(self.REGULAR_LIMIT * 1000), nx=True)
            return bool(is_set)
        except Exception as e:
            logger.error("Redis throttle error (reg): %s", e)
            return True

    async def _notify_throttle(self, event: TelegramObject) -> None:
        try:
            if hasattr(event, "answer"):
                await event.answer("Слишком много запросов. Подождите немного.")
            elif hasattr(event, "message") and hasattr(event.message, "answer"):
                await event.message.answer("Слишком много запросов. Подождите немного.")
        except Exception as e:
            logger.error("Failed to notify throttle: %s", e)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        state: FSMContext | None = data.get("state")
        current_state = None
        if state:
            try:
                current_state = await state.get_state()
            except Exception:
                pass

        if self._is_command(event):
            is_allowed = await self._check_command_throttle(user_id)
            if not is_allowed:
                await self._notify_throttle(event)
                return None
        elif current_state is not None:
            is_allowed = await self._check_fsm_throttle(user_id)
            if not is_allowed:
                await self._notify_throttle(event)
                return None
        else:
            is_allowed = await self._check_regular_throttle(user_id)
            if not is_allowed:
                await self._notify_throttle(event)
                return None

        return await handler(event, data)
