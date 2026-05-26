"""Handler for completing an order via inline button."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.order import OrderStatusEnum
from app.services.encryption import EncryptionService
from app.services.notification_service import NotificationService
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.database.models.user import RoleEnum, User

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("order_complete:"))
async def complete_order_callback(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Handle complete order inline button."""
    if user is None or user.role not in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
        await callback.answer("У вас недостаточно прав.", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    operator = user

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    order_service = OrderService(session, encryption)
    order = await order_service.get_order_by_id(order_id)

    if order is None:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if order.status != OrderStatusEnum.created:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    completed_order = await order_service.complete_order(order_id, operator.id)
    if completed_order is None:
        await callback.answer("Ошибка завершения.", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Заявка #{order_id} завершена оператором @{operator.username or 'N/A'}."
    )

    if order.chat_id and order.message_id:
        order_type_str = "покупку" if order.order_type.value == "buy" else "продажу"
        client_text = (
            f"✅ Ваша заявка #{order_id} на {order_type_str} {order.amount_usdt} USDT подтверждена!\n"
            f"К оплате: {order.total_fiat} RUB\n"
            f"Оператор: @{operator.username or 'N/A'}\n"
            f"Спасибо за обращение!"
        )
        try:
            await callback.bot.send_message(chat_id=order.chat_id, text=client_text)
        except Exception as e:
            logger.error(f"Failed to notify client about completed order #{order_id}: {e}")

    notif_service = NotificationService(session)
    await notif_service.notify_order_completed(callback.bot, completed_order, operator)

    await callback.answer("Заявка завершена.")
    logger.info(f"Order #{order_id} completed by operator {operator.telegram_id}")


@router.callback_query(F.data.startswith("order_admin_cancel:"))
async def admin_cancel_order_callback(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Handle admin/operator cancel order inline button."""
    if user is None or user.role not in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=operator+")
        await callback.answer("У вас недостаточно прав.", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    order_service = OrderService(session, None)
    order = await order_service.get_order_by_id(order_id)

    if order is None:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if order.status != OrderStatusEnum.created:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    cancelled_order = await order_service.cancel_order(order_id, 0)
    if cancelled_order is None:
        await callback.answer("Ошибка отмены.", show_alert=True)
        return

    await callback.message.edit_text(f"❌ Заявка #{order_id} отменена администратором.")

    if order.chat_id:
        try:
            await callback.bot.send_message(
                chat_id=order.chat_id,
                text=f"❌ Ваша заявка #{order_id} отменена администратором.",
            )
        except Exception as e:
            logger.error(f"Failed to notify client about cancelled order #{order_id}: {e}")

    await callback.answer("Заявка отменена.")
    logger.info(f"Order #{order_id} cancelled by admin/operator")
