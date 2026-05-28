"""Admin and SuperAdmin keyboard layouts."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from app.config import settings


def admin_keyboard(
    buy_enabled: bool = True,
    sell_enabled: bool = True,
    bot_enabled: bool = True,
    is_super_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """Main admin menu keyboard — compact 2-row layout.

    Management functions (toggles, rate changes, etc.) are in the inline
    panel triggered by ⚙️ Управление (see management_kb.py).
    """
    kb = [
        [KeyboardButton(text="💎 Web3 App", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
        [KeyboardButton(text="📋 Заявки"), KeyboardButton(text="📈 Статистика"), KeyboardButton(text="📊 Курсы")],
        [KeyboardButton(text="⚙️ Управление")],
    ]

    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
