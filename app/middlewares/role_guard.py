"""Role guard middleware — filters actions by user role hierarchy."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database.models.user import RoleEnum, User

_ROLE_HIERARCHY: dict[RoleEnum, int] = {
    RoleEnum.client: 0,
    RoleEnum.operator: 1,
    RoleEnum.admin: 2,
    RoleEnum.super_admin: 3,
}


class RoleFilter:
    """Filter that checks if user's role meets minimum required role level.

    Usage in router:
        router.message.filter(RoleFilter(min_role=RoleEnum.admin))
    """

    def __init__(self, min_role: RoleEnum) -> None:
        self.min_role = min_role
        self.min_level = _ROLE_HIERARCHY[min_role]

    async def __call__(self, message: TelegramObject, data: dict[str, Any]) -> bool:
        user: User | None = data.get("user")
        if user is None:
            return False
        user_level = _ROLE_HIERARCHY.get(user.role, 0)
        return user_level >= self.min_level


class RoleGuardMiddleware(BaseMiddleware):
    """Middleware that enforces role-based access.

    Reads 'required_role' from handler data to check access.
    Can be used on specific routers.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("user")
        required_role: RoleEnum | None = data.get("required_role")

        if required_role is None:
            return await handler(event, data)

        if user is None:
            return

        user_level = _ROLE_HIERARCHY.get(user.role, 0)
        required_level = _ROLE_HIERARCHY.get(required_role, 0)

        if user_level < required_level:
            from aiogram.types import CallbackQuery, Message

            if isinstance(event, CallbackQuery):
                await event.answer("У вас недостаточно прав.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("У вас недостаточно прав для этого действия.")
            return

        return await handler(event, data)
