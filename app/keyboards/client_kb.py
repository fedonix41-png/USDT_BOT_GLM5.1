"""Client keyboard layouts."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from app.config import settings


def client_keyboard(buy_enabled: bool = True, sell_enabled: bool = True) -> ReplyKeyboardMarkup:
    """Main client menu keyboard."""
    buy_text = "💰 Купить" if buy_enabled else "🛑 Закуп стоп"
    sell_text = "💸 Продать" if sell_enabled else "🛑 Продажа стоп"

    kb = [
        [KeyboardButton(text="💎 Web3 App", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
        [KeyboardButton(text=buy_text), KeyboardButton(text=sell_text)],
        [KeyboardButton(text="📊 Курсы"), KeyboardButton(text="📞 Поддержка")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
