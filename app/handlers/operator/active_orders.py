"""Handler for viewing active orders with pagination."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.keyboards.inline_kb import order_operator_kb, pagination_kb
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.utils.formatting import format_order_for_operator
from app.utils.pagination import calculate_pagination

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📋 Заявки")
async def show_active_orders(message: Message, session: AsyncSession) -> None:
    """Show first page of active orders."""
    order_service = OrderService(session, None)
    user_service = UserService(session)

    total = await order_service.count_active_orders()
    if total == 0:
        await message.answer("Нет активных заявок за последние 24 часа.")
        return

    orders = await order_service.get_active_orders(offset=0, limit=app_settings.ORDERS_PER_PAGE)

    for order in orders:
        user = await user_service.get_by_telegram_id(order.user.telegram_id if order.user else 0)
        text = format_order_for_operator(order, user)
        kb = order_operator_kb(order.id)
        await message.answer(text, reply_markup=kb)

    pagination = calculate_pagination(total, 0, app_settings.ORDERS_PER_PAGE)
    if pagination["has_next"]:
        pag_kb = pagination_kb(0, total, app_settings.ORDERS_PER_PAGE, "orders")
        await message.answer(f"Страница 1 из {pagination['total_pages']}", reply_markup=pag_kb)


@router.callback_query(F.data.startswith("page:orders:"))
async def paginate_orders(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle pagination for active orders."""
    offset = int(callback.data.split(":")[2])
    order_service = OrderService(session, None)
    user_service = UserService(session)

    total = await order_service.count_active_orders()
    orders = await order_service.get_active_orders(offset=offset, limit=app_settings.ORDERS_PER_PAGE)

    for order in orders:
        user = await user_service.get_by_telegram_id(order.user.telegram_id if order.user else 0)
        text = format_order_for_operator(order, user)
        kb = order_operator_kb(order.id)
        await callback.message.answer(text, reply_markup=kb)

    pagination = calculate_pagination(total, offset, app_settings.ORDERS_PER_PAGE)
    pag_kb = pagination_kb(offset, total, app_settings.ORDERS_PER_PAGE, "orders")
    page_num = pagination["current_page"]
    await callback.message.answer(
        f"Страница {page_num} из {pagination['total_pages']}", reply_markup=pag_kb
    )
    await callback.answer()
