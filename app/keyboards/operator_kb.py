"""Operator keyboard layouts."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def operator_keyboard() -> ReplyKeyboardMarkup:
    """Main operator menu keyboard."""
    kb = [
        [KeyboardButton(text="📋 Заявки"), KeyboardButton(text="📊 Курсы")],
        [KeyboardButton(text="📈 Статистика")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
