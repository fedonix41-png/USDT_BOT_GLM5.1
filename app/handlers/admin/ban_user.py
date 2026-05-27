"""Handlers for banning/unbanning users — FSM BanUserStates / UnbanUserStates.

FSM is started from the management panel (mgmt:ban_user / mgmt:unban_user callbacks).
"""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.fsm.role_states import BanUserStates, UnbanUserStates
from app.keyboards.cancel_kb import get_main_keyboard
from app.services.notification_service import NotificationService
from app.services.user_service import UserService
from app.utils.helpers import check_fsm_attempts, get_settings_flags, reset_fsm_attempts

logger = logging.getLogger(__name__)

router = Router()


@router.message(BanUserStates.waiting_target_user)
async def process_ban_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Process banning a user by Telegram ID."""
    try:
        target_telegram_id = int(message.text.strip())
    except ValueError:
        await check_fsm_attempts(
            state, message, "Введите корректный Telegram ID (число)."
        )
        return

    if target_telegram_id == message.from_user.id:
        await message.answer("Невозможно заблокировать самого себя.")
        await state.clear()
        return

    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={message.from_user.id}, command=ban_user, required_role=admin+")
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return

    user_service = UserService(session)
    target_user = await user_service.get_by_telegram_id(target_telegram_id)

    if target_user is None:
        await check_fsm_attempts(
            state, message, "Пользователь не найден. Он должен сначала запустить бота (/start)."
        )
        return

    if target_user.role in (RoleEnum.admin, RoleEnum.super_admin):
        await message.answer("Невозможно заблокировать администратора.")
        await state.clear()
        return

    if target_user.is_blocked:
        await message.answer("Пользователь уже заблокирован.")
        await state.clear()
        return

    updated_user = await user_service.block_user(target_user.id, user.id)
    if updated_user is None:
        await message.answer("Ошибка блокировки пользователя.")
        await state.clear()
        return

    try:
        await message.bot.send_message(
            chat_id=target_telegram_id,
            text="🚫 Вы заблокированы в боте обмена USDT.",
        )
    except Exception as e:
        logger.error(f"Failed to notify user {target_telegram_id} about ban: {e}")

    notif_service = NotificationService(session)
    await notif_service.notify_user_banned(message.bot, updated_user, True)

    username_str = f"@{updated_user.username}" if updated_user.username else f"ID: {target_telegram_id}"
    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"✅ Пользователь {username_str} заблокирован.", reply_markup=kb)
    await state.clear()
    logger.info(f"User {target_telegram_id} banned by {message.from_user.id}")


@router.message(UnbanUserStates.waiting_target_user)
async def process_unban_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Process unbanning a user by Telegram ID."""
    try:
        target_telegram_id = int(message.text.strip())
    except ValueError:
        await check_fsm_attempts(
            state, message, "Введите корректный Telegram ID (число)."
        )
        return

    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={message.from_user.id}, command=unban_user, required_role=admin+")
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return

    user_service = UserService(session)
    target_user = await user_service.get_by_telegram_id(target_telegram_id)

    if target_user is None:
        await check_fsm_attempts(
            state, message, "Пользователь не найден. Он должен сначала запустить бота (/start)."
        )
        return

    if not target_user.is_blocked:
        await message.answer("Пользователь не заблокирован.")
        await state.clear()
        return

    updated_user = await user_service.unblock_user(target_user.id, user.id)
    if updated_user is None:
        await message.answer("Ошибка разблокировки пользователя.")
        await state.clear()
        return

    try:
        await message.bot.send_message(
            chat_id=target_telegram_id,
            text="✅ Вы разблокированы в боте обмена USDT.",
        )
    except Exception as e:
        logger.error(f"Failed to notify user {target_telegram_id} about unban: {e}")

    notif_service = NotificationService(session)
    await notif_service.notify_user_banned(message.bot, updated_user, False)

    username_str = f"@{updated_user.username}" if updated_user.username else f"ID: {target_telegram_id}"
    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"✅ Пользователь {username_str} разблокирован.", reply_markup=kb)
    await state.clear()
    logger.info(f"User {target_telegram_id} unbanned by {message.from_user.id}")
