"""Operator keyboard layouts."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from app.config import settings


def operator_keyboard() -> ReplyKeyboardMarkup:
    """Main operator menu keyboard."""
    kb = [
        [KeyboardButton(text="💎 Web3 App", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
        [KeyboardButton(text="📋 Заявки"), KeyboardButton(text="📊 Курсы")],
        [KeyboardButton(text="📈 Статистика")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
