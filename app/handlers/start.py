"""Handler for /start command — user registration and main menu."""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings
from app.database.models.user import RoleEnum, User
from app.keyboards.admin_kb import admin_keyboard
from app.keyboards.client_kb import client_keyboard
from app.keyboards.operator_kb import operator_keyboard
from app.services.user_service import UserService
from app.utils.formatting import role_display_name

logger = logging.getLogger(__name__)

router = Router()


async def _get_settings_flags(session: AsyncSession) -> dict:
    """Get bot settings flags directly from DB."""
    flags = {"bot_enabled": True, "buy_enabled": True, "sell_enabled": True}
    for key in flags:
        result = await session.get(GlobalSettings, key)
        if result is not None:
            flags[key] = result.value == "1"
    return flags


async def _get_user(session: AsyncSession, message: Message) -> User:
    """Get or create user from message."""
    user_service = UserService(session)
    return await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """Handle /start command."""
    user = await _get_user(session, message)
    flags = await _get_settings_flags(session)

    role_name = role_display_name(user.role.value)
    welcome = (
        f"👋 Добро пожаловать в бот обмена USDT!\n\n"
        f"Ваш текущий статус: {role_name}\n\n"
        f"Выберите действие:"
    )

    if user.role == RoleEnum.client:
        kb = client_keyboard(buy_enabled=flags["buy_enabled"], sell_enabled=flags["sell_enabled"])
    elif user.role == RoleEnum.operator:
        kb = operator_keyboard()
    elif user.role in (RoleEnum.admin, RoleEnum.super_admin):
        kb = admin_keyboard(
            buy_enabled=flags["buy_enabled"],
            sell_enabled=flags["sell_enabled"],
            bot_enabled=flags["bot_enabled"],
            is_super_admin=user.role == RoleEnum.super_admin,
        )
    else:
        kb = client_keyboard()

    await message.answer(welcome, reply_markup=kb)
    logger.info(f"User {user.telegram_id} started bot, role={user.role.value}")
