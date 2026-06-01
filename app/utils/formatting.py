"""Message formatting utilities for the USDT exchange bot."""

from datetime import datetime

from app.database.models.order import Order, OrderTypeEnum
from app.database.models.user import User


def format_order_message(order: Order, user: User | None = None, payment_link: str = "") -> str:
    """Format an order message for the client."""
    type_str = "покупку" if order.order_type == OrderTypeEnum.buy else "продажу"
    type_emoji = "🟢 Покупка" if order.order_type == OrderTypeEnum.buy else "🔴 Продажа"

    parts = [
        f"📌 Заявка на {type_str} USDT #{order.id}",
        "",
        f"Сумма: {order.amount_usdt} USDT",
        f"Курс: {order.rate} RUB/USDT",
        f"К оплате: {order.total_fiat} RUB",
    ]

    if payment_link:
        parts.extend(["", "Реквизиты оплаты:", payment_link])

    parts.extend(["", "После оплаты ожидайте подтверждения оператором."])
    return "\n".join(parts)


def format_order_for_operator(order: Order, user: User | None = None, decrypted_details: str = "") -> str:
    """Format an order for the operator's active orders list."""
    type_emoji = "🟢 Покупка" if order.order_type == OrderTypeEnum.buy else "🔴 Продажа"
    if user and user.username:
        username = f"@{user.username}"
    elif user and user.phone:
        username = f"📱 {user.phone}"
    else:
        username = "N/A"
    tg_id = user.telegram_id if user else "N/A"

    is_paid_from_balance = False
    if decrypted_details and decrypted_details.startswith("[BALANCE_PAID]"):
        is_paid_from_balance = True
        decrypted_details = decrypted_details.replace("[BALANCE_PAID]", "", 1)

    details_line = f"Реквизиты/Кошелек: {decrypted_details}\n" if decrypted_details else ""

    payment_method_line = ""
    if order.order_type == OrderTypeEnum.sell:
        method = "Списано с баланса Mini App" if is_paid_from_balance else "Внешний перевод USDT на кошелек"
        payment_method_line = f"Метод оплаты: {method}\n"

    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Заявка #{order.id} | {type_emoji}\n"
        f"Клиент: {username} (ID: {tg_id})\n"
        f"Сумма: {order.amount_usdt} USDT\n"
        f"К оплате: {order.total_fiat} RUB\n"
        f"{payment_method_line}"
        f"{details_line}"
        f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else 'N/A'}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_statistics(stats: dict, start: datetime, end: datetime) -> str:
    """Format statistics message."""
    return (
        f"📊 Статистика с {start.strftime('%d.%m.%Y')} по {end.strftime('%d.%m.%Y')}:\n"
        f"Покупок: {stats['count_buy']} на сумму {stats['sum_buy']} USDT\n"
        f"Продаж: {stats['count_sell']} на сумму {stats['sum_sell']} USDT\n"
        f"Всего заявок: {stats['total']}"
    )


def format_rates(buy_rate: str | None, sell_rate: str | None) -> str:
    """Format rates display message."""
    buy_str = f"{buy_rate} RUB/USDT" if buy_rate else "Не установлен"
    sell_str = f"{sell_rate} RUB/USDT" if sell_rate else "Не установлен"
    return (
        f"📊 Актуальные курсы:\n"
        f"Покупка: {buy_str}\n"
        f"Продажа: {sell_str}"
    )


def role_display_name(role: str) -> str:
    """Get a human-readable role name in Russian."""
    names = {
        "super_admin": "Суперадмин",
        "admin": "Администратор",
        "operator": "Оператор",
        "client": "Клиент",
    }
    return names.get(role, role)
