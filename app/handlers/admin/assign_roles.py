"""Handlers for assigning operator/admin roles — FSM AssignOperatorStates / AssignAdminStates.

FSM is now started from the management panel (mgmt:assign_operator / mgmt:assign_admin callbacks).
"""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.fsm.role_states import AssignAdminStates, AssignOperatorStates
from app.keyboards.cancel_kb import get_main_keyboard
from app.services.notification_service import NotificationService
from app.services.user_service import UserService
from app.utils.helpers import check_fsm_attempts, get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


@router.message(AssignOperatorStates.waiting_target_user)
async def process_assign_operator(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Process assigning operator role."""
    try:
        target_telegram_id = int(message.text.strip())
    except ValueError:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Введите корректный Telegram ID (число)."
        )
        return

    user_service = UserService(session)
    target_user = await user_service.get_by_telegram_id(target_telegram_id)

    if target_user is None:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Пользователь не найден. Он должен сначала запустить бота (/start)."
        )
        return

    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={message.from_user.id}, command=assign_operator, required_role=admin+")
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return

    updated_user = await user_service.set_role(target_user.id, RoleEnum.operator, user.id)
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
    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"✅ Пользователь {username_str} теперь Оператор.", reply_markup=kb)
    await state.clear()
    logger.info(f"User {target_telegram_id} assigned as Operator by {message.from_user.id}")


@router.message(AssignAdminStates.waiting_target_user)
async def process_assign_admin(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Process assigning admin role."""
    try:
        target_telegram_id = int(message.text.strip())
    except ValueError:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Введите корректный Telegram ID (число)."
        )
        return

    user_service = UserService(session)
    if user is None or user.role != RoleEnum.super_admin:
        logger.warning(f"Unauthorized access attempt: user_id={message.from_user.id}, command=assign_admin, required_role=super_admin")
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return

    target_user = await user_service.get_by_telegram_id(target_telegram_id)
    if target_user is None:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Пользователь не найден. Он должен сначала запустить бота (/start)."
        )
        return

    updated_user = await user_service.set_role(target_user.id, RoleEnum.admin, user.id)
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
    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=True,
    )
    await message.answer(f"✅ Пользователь {username_str} теперь Админ.", reply_markup=kb)
    await state.clear()
    logger.info(f"User {target_telegram_id} assigned as Admin by SuperAdmin {message.from_user.id}")
