"""Inline keyboard layouts."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.callback_data import OrderAction, Pagination, LinkAction, NotificationAction


def order_client_kb(order_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for client's order message (cancel + broken link)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔗 Ссылка не работает", callback_data=OrderAction(action="broken_link", order_id=order_id).pack()),
                InlineKeyboardButton(text="❌ Отменить заявку", callback_data=OrderAction(action="cancel", order_id=order_id).pack()),
            ]
        ]
    )


def order_operator_kb(order_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for operator's active order (complete + cancel)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Завершить", callback_data=OrderAction(action="complete", order_id=order_id).pack()),
                InlineKeyboardButton(text="❌ Отменить", callback_data=OrderAction(action="admin_cancel", order_id=order_id).pack()),
            ]
        ]
    )


def pagination_kb(current_offset: int, total: int, per_page: int, list_type: str = "orders") -> InlineKeyboardMarkup:
    """Pagination keyboard with back/forward buttons."""
    buttons = []
    back_btn = InlineKeyboardButton(text="◀️ Назад", callback_data=Pagination(list_type=list_type, offset=current_offset - per_page).pack())
    forward_btn = InlineKeyboardButton(text="Вперёд ▶️", callback_data=Pagination(list_type=list_type, offset=current_offset + per_page).pack())

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
                InlineKeyboardButton(text="🟢 Покупка", callback_data=LinkAction(action="type", type="buy").pack()),
                InlineKeyboardButton(text="🔴 Продажа", callback_data=LinkAction(action="type", type="sell").pack()),
            ]
        ]
    )


def chat_list_kb(chats: list) -> InlineKeyboardMarkup:
    """Keyboard for selecting a chat to delete from notification list."""
    buttons = []
    for chat in chats:
        buttons.append([InlineKeyboardButton(text=f"Чат {chat.chat_id}", callback_data=NotificationAction(action="del", chat_id=chat.id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def notification_chats_menu_kb() -> InlineKeyboardMarkup:
    """Submenu for notification chats management with a Back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Список чатов", callback_data=NotificationAction(action="list").pack()),
                InlineKeyboardButton(text="➕ Добавить чат", callback_data=NotificationAction(action="add").pack()),
            ],
            [InlineKeyboardButton(text="➖ Удалить чат", callback_data=NotificationAction(action="delete").pack())],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=NotificationAction(action="back").pack())],
        ]
    )
