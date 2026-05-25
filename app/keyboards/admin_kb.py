"""Admin and SuperAdmin keyboard layouts."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_keyboard(
    buy_enabled: bool = True,
    sell_enabled: bool = True,
    bot_enabled: bool = True,
    is_super_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """Main admin menu keyboard."""
    buy_btn_text = "✅ Закуп вкл" if buy_enabled else "⏸ Стоп закуп"
    sell_btn_text = "✅ Продажа вкл" if sell_enabled else "⏸ Стоп продажа"
    bot_btn_text = "🛑 Отключить бота" if bot_enabled else "✅ Включить бота"

    kb = [
        [KeyboardButton(text="📋 Активные заявки"), KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📊 Курсы")],
        [KeyboardButton(text="🔄 Сменить курс (покупка)"), KeyboardButton(text="🔄 Сменить курс (продажа)")],
        [KeyboardButton(text="🔗 Сменить реквизиты")],
        [KeyboardButton(text=buy_btn_text), KeyboardButton(text=sell_btn_text)],
        [KeyboardButton(text=bot_btn_text)],
        [KeyboardButton(text="➕ Чаты уведомлений")],
        [KeyboardButton(text="👤 Сделать Оператором")],
    ]

    if is_super_admin:
        kb.append([KeyboardButton(text="👑 Сделать Админом")])

    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
