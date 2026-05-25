"""Handler for cancelling an order via inline button."""

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import OrderStatusEnum
from app.services.order_service import OrderService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("order_cancel:"))
async def cancel_order_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle cancel order inline button."""
    order_id = int(callback.data.split(":")[1])
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)

    if user is None:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    order_service = OrderService(session, None)
    order = await order_service.get_order_by_id(order_id)

    if order is None:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if order.status != OrderStatusEnum.created:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    if order.user_id != user.id:
        await callback.answer("Вы можете отменить только свои заявки.", show_alert=True)
        return

    cancelled_order = await order_service.cancel_order(order_id, user.id)
    if cancelled_order is None:
        await callback.answer("Ошибка отмены.", show_alert=True)
        return

    await callback.message.edit_text(f"❌ Заявка #{order_id} отменена.")
    await callback.answer("Заявка отменена.")
    logger.info(f"Order #{order_id} cancelled by user {user.telegram_id}")
