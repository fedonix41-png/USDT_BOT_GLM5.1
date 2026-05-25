"""Handlers for assigning operator/admin roles — FSM AssignOperatorStates / AssignAdminStates."""

import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings
from app.database.models.user import RoleEnum, User
from app.fsm.role_states import AssignAdminStates, AssignOperatorStates
from app.keyboards.admin_kb import admin_keyboard
from app.services.notification_service import NotificationService
from app.services.user_service import UserService
from app.utils.formatting import role_display_name

logger = logging.getLogger(__name__)

router = Router()


async def _get_settings_flags(session: AsyncSession) -> dict:
    flags = {"bot_enabled": True, "buy_enabled": True, "sell_enabled": True}
    for key in flags:
        result = await session.get(GlobalSettings, key)
        if result is not None:
            flags[key] = result.value == "1"
    return flags


@router.message(F.text == "👤 Сделать Оператором", StateFilter(None))
async def start_assign_operator(message: Message, state: FSMContext) -> None:
    """Initiate assign operator FSM."""
    await state.set_state(AssignOperatorStates.waiting_target_user)
    await message.answer("Введите Telegram ID пользователя или перешлите его контакт:")


@router.message(AssignOperatorStates.waiting_target_user)
async def process_assign_operator(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process assigning operator role."""
    try:
        target_telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите корректный Telegram ID (число).")
        return

    user_service = UserService(session)
    target_user = await user_service.get_by_telegram_id(target_telegram_id)

    if target_user is None:
        await message.answer("Пользователь не найден. Он должен сначала запустить бота (/start).")
        return

    admin = await user_service.get_by_telegram_id(message.from_user.id)
    if admin is None:
        await message.answer("Ошибка.")
        await state.clear()
        return

    updated_user = await user_service.set_role(target_user.id, RoleEnum.operator, admin.id)
    if updated_user is None:
        await message.answer("Ошибка назначения роли.")
        await state.clear()
        return

    try:
        await message.bot.send_message(
            chat_id=target_telegram_id,
            text="👤 Вы назначены Оператором бота обмена USDT.",
        )
    except Exception as e:
        logger.error(f"Failed to notify user {target_telegram_id} about role assignment: {e}")

    notif_service = NotificationService(session)
    await notif_service.notify_role_assigned(message.bot, updated_user, "Оператор")

    username_str = f"@{updated_user.username}" if updated_user.username else f"ID: {target_telegram_id}"
    flags = await _get_settings_flags(session)
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=admin.role == RoleEnum.super_admin,
    )
    await message.answer(f"✅ Пользователь {username_str} теперь Оператор.", reply_markup=kb)
    await state.clear()
    logger.info(f"User {target_telegram_id} assigned as Operator by {message.from_user.id}")


@router.message(F.text == "👑 Сделать Админом", StateFilter(None))
async def start_assign_admin(message: Message, state: FSMContext) -> None:
    """Initiate assign admin FSM (only for SuperAdmin)."""
    await state.set_state(AssignAdminStates.waiting_target_user)
    await message.answer("Введите Telegram ID пользователя или перешлите его контакт:")


@router.message(AssignAdminStates.waiting_target_user)
async def process_assign_admin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process assigning admin role."""
    try:
        target_telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите корректный Telegram ID (число).")
        return

    user_service = UserService(session)
    caller = await user_service.get_by_telegram_id(message.from_user.id)
    if caller is None or caller.role != RoleEnum.super_admin:
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return

    target_user = await user_service.get_by_telegram_id(target_telegram_id)
    if target_user is None:
        await message.answer("Пользователь не найден. Он должен сначала запустить бота (/start).")
        return

    updated_user = await user_service.set_role(target_user.id, RoleEnum.admin, caller.id)
    if updated_user is None:
        await message.answer("Ошибка назначения роли.")
        await state.clear()
        return

    try:
        await message.bot.send_message(
            chat_id=target_telegram_id,
            text="👑 Вы назначены Администратором бота обмена USDT.",
        )
    except Exception as e:
        logger.error(f"Failed to notify user {target_telegram_id} about admin role: {e}")

    notif_service = NotificationService(session)
    await notif_service.notify_role_assigned(message.bot, updated_user, "Администратор")

    username_str = f"@{updated_user.username}" if updated_user.username else f"ID: {target_telegram_id}"
    flags = await _get_settings_flags(session)
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=True,
    )
    await message.answer(f"✅ Пользователь {username_str} теперь Админ.", reply_markup=kb)
    await state.clear()
    logger.info(f"User {target_telegram_id} assigned as Admin by SuperAdmin {message.from_user.id}")
