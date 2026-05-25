"""Cancel reply keyboard and menu restoration helpers."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.database.models.user import RoleEnum
from app.keyboards.admin_kb import admin_keyboard
from app.keyboards.client_kb import client_keyboard
from app.keyboards.operator_kb import operator_keyboard

CANCEL_BUTTON_TEXT = "❌ Отмена"


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard with a single Cancel button — shown during FSM flows."""
    kb = [[KeyboardButton(text=CANCEL_BUTTON_TEXT)]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_main_keyboard(
    role: RoleEnum,
    buy_enabled: bool = True,
    sell_enabled: bool = True,
    bot_enabled: bool = True,
    is_super_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """Return the appropriate main menu keyboard based on user role."""
    if role == RoleEnum.client:
        return client_keyboard(buy_enabled=buy_enabled, sell_enabled=sell_enabled)
    elif role == RoleEnum.operator:
        return operator_keyboard()
    elif role in (RoleEnum.admin, RoleEnum.super_admin):
        return admin_keyboard(
            buy_enabled=buy_enabled,
            sell_enabled=sell_enabled,
            bot_enabled=bot_enabled,
            is_super_admin=is_super_admin,
        )
    return client_keyboard()
