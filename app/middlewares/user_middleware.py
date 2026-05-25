"""Middleware for loading user from database into handler data."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.repositories.user_repo import UserRepository


class UserMiddleware(BaseMiddleware):
    """Loads the current user from the database and puts it in data['user'].
    
    If the user is not found in the DB (hasn't started the bot yet),
    data['user'] will be None. The /start handler will create the user.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")
        data["user"] = None

        if session is None:
            return await handler(event, data)

        from_user = None
        if hasattr(event, "from_user") and event.from_user:
            from_user = event.from_user
        elif hasattr(event, "message") and hasattr(event.message, "from_user"):
            from_user = event.message.from_user

        if from_user is not None:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(from_user.id)
            data["user"] = user

        return await handler(event, data)
