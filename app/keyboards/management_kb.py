"""Inline keyboard for admin/super_admin management panel."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def management_keyboard(
    buy_enabled: bool = True,
    sell_enabled: bool = True,
    bot_enabled: bool = True,
    is_super_admin: bool = False,
) -> InlineKeyboardMarkup:
    """Inline management panel — toggles update in place, actions start FSM."""
    buy_btn = "✅ Закуп вкл" if buy_enabled else "⏸ Стоп закуп"
    sell_btn = "✅ Продажа вкл" if sell_enabled else "⏸ Стоп продажа"
    bot_btn = "🛑 Отключить бота" if bot_enabled else "✅ Включить бота"

    kb = [
        [
            InlineKeyboardButton(text="🔄 Курс покупки", callback_data="mgmt:rate_buy"),
            InlineKeyboardButton(text="🔄 Курс продажи", callback_data="mgmt:rate_sell"),
        ],
        [InlineKeyboardButton(text="🔗 Реквизиты", callback_data="mgmt:links")],
        [
            InlineKeyboardButton(text=buy_btn, callback_data="mgmt:toggle_buy"),
            InlineKeyboardButton(text=sell_btn, callback_data="mgmt:toggle_sell"),
        ],
        [InlineKeyboardButton(text=bot_btn, callback_data="mgmt:toggle_bot")],
        [
            InlineKeyboardButton(text="➕ Чаты", callback_data="mgmt:chats"),
            InlineKeyboardButton(text="👤 Оператор", callback_data="mgmt:assign_operator"),
        ],
    ]

    if is_super_admin:
        kb.append([InlineKeyboardButton(text="👑 Админ", callback_data="mgmt:assign_admin")])

    kb.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="mgmt:close")])

    return InlineKeyboardMarkup(inline_keyboard=kb)
