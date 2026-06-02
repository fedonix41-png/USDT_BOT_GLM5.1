"""Inline keyboard for admin/super_admin management panel."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.callback_data import ManagementAction


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
            InlineKeyboardButton(text="🔄 Курс покупки", callback_data=ManagementAction(action="rate_buy").pack()),
            InlineKeyboardButton(text="🔄 Курс продажи", callback_data=ManagementAction(action="rate_sell").pack()),
        ],
        [InlineKeyboardButton(text="🔗 Реквизиты", callback_data=ManagementAction(action="links").pack())],
        [
            InlineKeyboardButton(text=buy_btn, callback_data=ManagementAction(action="toggle_buy").pack()),
            InlineKeyboardButton(text=sell_btn, callback_data=ManagementAction(action="toggle_sell").pack()),
        ],
        [InlineKeyboardButton(text=bot_btn, callback_data=ManagementAction(action="toggle_bot").pack())],
        [
            InlineKeyboardButton(text="➕ Чаты", callback_data=ManagementAction(action="chats").pack()),
        ],
        [
            InlineKeyboardButton(text="👤 Оператор", callback_data=ManagementAction(action="assign_operator").pack()),
            InlineKeyboardButton(text="👤⬇️ Снять оператора", callback_data=ManagementAction(action="demote_operator").pack()),
        ],
    ]

    if is_super_admin:
        kb.append([
            InlineKeyboardButton(text="👑 Админ", callback_data=ManagementAction(action="assign_admin").pack()),
            InlineKeyboardButton(text="👑⬇️ Снять админа", callback_data=ManagementAction(action="demote_admin").pack()),
        ])

    kb.append([
        InlineKeyboardButton(text="🚫 Забанить", callback_data=ManagementAction(action="ban_user").pack()),
        InlineKeyboardButton(text="✅ Разбанить", callback_data=ManagementAction(action="unban_user").pack()),
    ])

    kb.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data=ManagementAction(action="close").pack())])

    return InlineKeyboardMarkup(inline_keyboard=kb)
