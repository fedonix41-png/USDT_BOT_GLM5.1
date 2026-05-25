"""Middleware for injecting async DB session into handler data."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.database.engine import async_session_maker

logger = logging.getLogger(__name__)


class DBSessionMiddleware(BaseMiddleware):
    """Injects an AsyncSession into handler data as 'session'.
    
    Handles database connection errors gracefully, notifying the user
    when the database is unavailable.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            async with async_session_maker() as session:
                data["session"] = session
                try:
                    result = await handler(event, data)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        except (DBAPIError, SQLAlchemyError, OSError) as e:
            logger.error("Database connection error: %s", e)
            
            try:
                if hasattr(event, "answer"):
                    await event.answer("Сервис временно недоступен. Попробуйте позже.")
                elif hasattr(event, "message") and hasattr(event.message, "answer"):
                    await event.message.answer("Сервис временно недоступен. Попробуйте позже.")
            except Exception as notify_error:
                logger.error("Failed to notify user about DB error: %s", notify_error)
            
            return None
