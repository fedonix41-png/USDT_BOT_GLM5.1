"""Handler for toggling bot_enabled, buy_enabled, sell_enabled flags."""

import logging

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.global_settings import GlobalSettings
from app.database.models.user import RoleEnum, User
from app.keyboards.admin_kb import admin_keyboard
from app.services.encryption import EncryptionService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text.in_({"⏸ Стоп закуп", "✅ Закуп вкл"}))
async def toggle_buy(message: Message, session: AsyncSession) -> None:
    """Toggle buy_enabled flag."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка.")
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    now_enabled = await settings_service.toggle_flag("buy_enabled", user.id)

    text = "✅ Покупка USDT возобновлена." if now_enabled else "🛑 Покупка USDT остановлена."

    flags = {
        "bot_enabled": True,
        "buy_enabled": now_enabled,
        "sell_enabled": await settings_service.is_sell_enabled(),
    }
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(text, reply_markup=kb)
    logger.info(f"Buy toggled to {now_enabled} by user {user.telegram_id}")


@router.message(F.text.in_({"⏸ Стоп продажа", "✅ Продажа вкл"}))
async def toggle_sell(message: Message, session: AsyncSession) -> None:
    """Toggle sell_enabled flag."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка.")
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    now_enabled = await settings_service.toggle_flag("sell_enabled", user.id)

    text = "✅ Продажа USDT возобновлена." if now_enabled else "🛑 Продажа USDT остановлена."

    flags = {
        "bot_enabled": await settings_service.is_bot_enabled(),
        "buy_enabled": await settings_service.is_buy_enabled(),
        "sell_enabled": now_enabled,
    }
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(text, reply_markup=kb)
    logger.info(f"Sell toggled to {now_enabled} by user {user.telegram_id}")


@router.message(F.text.in_({"🛑 Отключить бота", "✅ Включить бота"}))
async def toggle_bot(message: Message, session: AsyncSession) -> None:
    """Toggle bot_enabled flag."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка.")
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    now_enabled = await settings_service.toggle_flag("bot_enabled", user.id)

    if now_enabled:
        text = "✅ Бот включён."
    else:
        text = "🛑 Бот отключён для клиентов. Администраторы могут продолжать работу."

    flags = {
        "bot_enabled": now_enabled,
        "buy_enabled": await settings_service.is_buy_enabled(),
        "sell_enabled": await settings_service.is_sell_enabled(),
    }
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(text, reply_markup=kb)
    logger.info(f"Bot toggled to {now_enabled} by user {user.telegram_id}")
