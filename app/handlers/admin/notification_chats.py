"""Handler for managing notification chats — add, list, delete.

FSM is now started from the management panel (mgmt:chats callback).
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.keyboards.cancel_kb import cancel_keyboard, get_main_keyboard
from app.keyboards.inline_kb import chat_list_kb
from app.services.notification_service import NotificationService
from app.services.user_service import UserService
from app.utils.helpers import get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


class NotificationChatStates(StatesGroup):
    waiting_chat_id = State()


@router.callback_query(F.data == "notif_list")
async def list_chats(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """List all notification chats."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
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
async def start_add_chat(callback: CallbackQuery, state: FSMContext, user: User | None) -> None:
    """Start adding a notification chat."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    await state.set_state(NotificationChatStates.waiting_chat_id)
    await callback.message.answer(
        "Перешлите сообщение из нужного чата или введите Chat ID:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(NotificationChatStates.waiting_chat_id)
async def process_add_chat(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
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
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={message.from_user.id}, command=add_chat, required_role=admin+")
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return

    notif_service = NotificationService(session)
    existing = await notif_service.get_by_chat_id(chat_id)
    if existing:
        await message.answer(f"Чат {chat_id} уже добавлен для уведомлений.")
    else:
        await notif_service.add_chat(chat_id=chat_id, added_by=user.id)
        await message.answer(f"✅ Чат {chat_id} добавлен для уведомлений.")

    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer("Выберите действие:", reply_markup=kb)

    await state.clear()
    logger.info(f"Notification chat {chat_id} added by user {message.from_user.id}")


@router.callback_query(F.data == "notif_delete")
async def start_delete_chat(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Start deleting a notification chat — show list."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
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
async def delete_chat(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Delete selected notification chat."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
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


@router.callback_query(F.data == "notif_back")
async def back_from_notif_menu(callback: CallbackQuery) -> None:
    """Back button from notification chats submenu — dismiss inline keyboard."""
    await callback.message.edit_text("Управление чатами закрыто.")
    await callback.answer()
