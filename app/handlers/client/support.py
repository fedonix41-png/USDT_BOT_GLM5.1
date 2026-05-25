"""Handler for support chat — FSM SupportStates."""

import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.fsm.support_states import SupportStates
from app.keyboards.cancel_kb import cancel_keyboard, get_main_keyboard
from app.services.notification_service import NotificationService
from app.utils.helpers import get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📞 Поддержка", StateFilter(None))
async def start_support(message: Message, state: FSMContext) -> None:
    """Initiate support FSM."""
    await state.set_state(SupportStates.waiting_message)
    await message.answer(
        "Напишите ваш вопрос, и мы ответим в ближайшее время.",
        reply_markup=cancel_keyboard(),
    )


@router.message(SupportStates.waiting_message)
async def process_support_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Forward support message to notification chats."""
    if user is None:
        await message.answer("Ошибка. Попробуйте снова.")
        await state.clear()
        return

    notif_service = NotificationService(session)
    bot = message.bot
    username = user.username or "N/A"
    text = (
        f"📩 Обращение в поддержку от @{username} (ID: {user.telegram_id}):\n"
        f"{message.text}"
    )
    await notif_service.send_to_all_chats(bot, text)

    # Restore main menu keyboard
    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer("Ваше сообщение передано в поддержку. Ожидайте ответа.", reply_markup=kb)

    await state.clear()
    logger.info(f"Support message from user {user.telegram_id}")
