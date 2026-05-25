"""Handler for support chat — FSM SupportStates."""

import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.fsm.support_states import SupportStates
from app.services.notification_service import NotificationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📞 Поддержка", StateFilter(None))
async def start_support(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Initiate support FSM."""
    await state.set_state(SupportStates.waiting_message)
    await message.answer("Напишите ваш вопрос, и мы ответим в ближайшее время.")


@router.message(SupportStates.waiting_message)
async def process_support_message(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Forward support message to notification chats."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

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
    await message.answer("Ваше сообщение передано в поддержку. Ожидайте ответа.")
    await state.clear()
    logger.info(f"Support message from user {user.telegram_id}")
