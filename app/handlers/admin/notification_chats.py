"""Handler for managing notification chats — add, list, delete."""

import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.user import RoleEnum
from app.fsm.links_states import ChangeLinksStates
from app.keyboards.inline_kb import chat_list_kb, notification_chats_menu_kb
from app.services.notification_service import NotificationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


class NotificationChatStates(StatesGroup):
    waiting_chat_id = State()


@router.message(F.text == "➕ Чаты уведомлений")
async def notification_chats_menu(message: Message) -> None:
    """Show notification chats management menu."""
    kb = notification_chats_menu_kb()
    await message.answer("Управление чатами уведомлений:", reply_markup=kb)


@router.callback_query(F.data == "notif_list")
async def list_chats(callback: CallbackQuery, session: AsyncSession) -> None:
    """List all notification chats."""
    notif_service = NotificationService(session)
    chats = await notif_service.get_all_chats()

    if not chats:
        await callback.message.answer("Нет добавленных чатов.")
    else:
        text = "📋 Чаты уведомлений:\n"
        for chat in chats:
            text += f"  • Chat ID: {chat.chat_id}\n"
        await callback.message.answer(text)

    await callback.answer()


@router.callback_query(F.data == "notif_add")
async def start_add_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding a notification chat."""
    await state.set_state(NotificationChatStates.waiting_chat_id)
    await callback.message.answer("Перешлите сообщение из нужного чата или введите Chat ID:")
    await callback.answer()


@router.message(NotificationChatStates.waiting_chat_id)
async def process_add_chat(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process adding a notification chat."""
    try:
        chat_id = int(message.text.strip())
    except (ValueError, AttributeError):
        if message.forward_from_chat:
            chat_id = message.forward_from_chat.id
        else:
            await message.answer("Введите корректный Chat ID (число) или перешлите сообщение из чата.")
            return

    try:
        member = await message.bot.get_chat_member(chat_id=chat_id, user_id=message.bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer("Бот не является администратором в этом чате. Добавьте бота в чат как администратор.")
            return
    except Exception as e:
        await message.answer(f"Не удалось проверить права бота в чате: {e}")
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    notif_service = NotificationService(session)
    existing = await notif_service.get_by_chat_id(chat_id)
    if existing:
        await message.answer(f"Чат {chat_id} уже добавлен для уведомлений.")
    else:
        await notif_service.add_chat(chat_id=chat_id, added_by=user.id)
        await message.answer(f"✅ Чат {chat_id} добавлен для уведомлений.")

    await state.clear()
    logger.info(f"Notification chat {chat_id} added by user {message.from_user.id}")


@router.callback_query(F.data == "notif_delete")
async def start_delete_chat(callback: CallbackQuery, session: AsyncSession) -> None:
    """Start deleting a notification chat — show list."""
    notif_service = NotificationService(session)
    chats = await notif_service.get_all_chats()

    if not chats:
        await callback.message.answer("Нет добавленных чатов.")
        await callback.answer()
        return

    kb = chat_list_kb(chats)
    await callback.message.answer("Выберите чат для удаления:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("chat_del:"))
async def delete_chat(callback: CallbackQuery, session: AsyncSession) -> None:
    """Delete selected notification chat."""
    chat_db_id = int(callback.data.split(":")[1])
    notif_service = NotificationService(session)

    chat = await notif_service.get_all_chats()
    target = None
    for c in chat:
        if c.id == chat_db_id:
            target = c
            break

    if target is None:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    success = await notif_service.remove_chat(target.chat_id)
    if success:
        await callback.message.edit_text(f"✅ Чат {target.chat_id} удалён из уведомлений.")
        logger.info(f"Notification chat {target.chat_id} deleted")
    else:
        await callback.answer("Ошибка удаления.", show_alert=True)
