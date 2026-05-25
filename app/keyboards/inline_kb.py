"""Inline keyboard layouts."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def order_client_kb(order_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for client's order message (cancel + broken link)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔗 Ссылка не работает", callback_data=f"order_broken_link:{order_id}"),
                InlineKeyboardButton(text="❌ Отменить заявку", callback_data=f"order_cancel:{order_id}"),
            ]
        ]
    )


def order_operator_kb(order_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for operator's active order (complete + cancel)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Завершить", callback_data=f"order_complete:{order_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"order_admin_cancel:{order_id}"),
            ]
        ]
    )


def pagination_kb(current_offset: int, total: int, per_page: int, list_type: str = "orders") -> InlineKeyboardMarkup:
    """Pagination keyboard with back/forward buttons."""
    buttons = []
    back_btn = InlineKeyboardButton(text="◀️ Назад", callback_data=f"page:{list_type}:{current_offset - per_page}")
    forward_btn = InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"page:{list_type}:{current_offset + per_page}")

    row = []
    if current_offset > 0:
        row.append(back_btn)
    if current_offset + per_page < total:
        row.append(forward_btn)
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def link_type_kb() -> InlineKeyboardMarkup:
    """Keyboard for choosing link type (buy/sell) when changing payment links."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Покупка", callback_data="link_type:buy"),
                InlineKeyboardButton(text="🔴 Продажа", callback_data="link_type:sell"),
            ]
        ]
    )


def chat_list_kb(chats: list) -> InlineKeyboardMarkup:
    """Keyboard for selecting a chat to delete from notification list."""
    buttons = []
    for chat in chats:
        buttons.append([InlineKeyboardButton(text=f"Чат {chat.chat_id}", callback_data=f"chat_del:{chat.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def notification_chats_menu_kb() -> InlineKeyboardMarkup:
    """Submenu for notification chats management with a Back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Список чатов", callback_data="notif_list"),
                InlineKeyboardButton(text="➕ Добавить чат", callback_data="notif_add"),
            ],
            [InlineKeyboardButton(text="➖ Удалить чат", callback_data="notif_delete")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="notif_back")],
        ]
    )
