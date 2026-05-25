"""Client keyboard layouts."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def client_keyboard(buy_enabled: bool = True, sell_enabled: bool = True) -> ReplyKeyboardMarkup:
    """Main client menu keyboard."""
    buy_text = "💰 Купить USDT" if buy_enabled else "🛑 Закуп остановлен"
    sell_text = "💸 Продать USDT" if sell_enabled else "🛑 Продажа остановлена"

    kb = [
        [KeyboardButton(text=buy_text), KeyboardButton(text=sell_text)],
        [KeyboardButton(text="📊 Курсы"), KeyboardButton(text="📞 Поддержка")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
