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
    """Rate limiting middleware to prevent spam.
    
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
        self._last_command: dict[int, float] = defaultdict(float)
        self._fsm_history: dict[int, list[float]] = defaultdict(list)
        self._last_message: dict[int, float] = defaultdict(float)

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

    def _check_command_throttle(self, user_id: int) -> bool:
        now = time.monotonic()
        last = self._last_command[user_id]
        if now - last < self.COMMAND_LIMIT:
            return False
        self._last_command[user_id] = now
        return True

    def _check_fsm_throttle(self, user_id: int) -> bool:
        now = time.monotonic()
        history = self._fsm_history[user_id]
        history[:] = [t for t in history if now - t < self.FSM_WINDOW]
        if len(history) >= self.FSM_LIMIT:
            return False
        history.append(now)
        return True

    def _check_regular_throttle(self, user_id: int) -> bool:
        now = time.monotonic()
        last = self._last_message[user_id]
        if now - last < self.REGULAR_LIMIT:
            return False
        self._last_message[user_id] = now
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
            if not self._check_command_throttle(user_id):
                await self._notify_throttle(event)
                return None
        elif current_state is not None:
            if not self._check_fsm_throttle(user_id):
                await self._notify_throttle(event)
                return None
        else:
            if not self._check_regular_throttle(user_id):
                await self._notify_throttle(event)
                return None

        return await handler(event, data)
