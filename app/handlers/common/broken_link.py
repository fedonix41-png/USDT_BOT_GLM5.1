"""Handler for 'Link not working' inline button."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.user import User
from app.services.encryption import EncryptionService
from app.services.notification_service import NotificationService
from app.services.order_service import OrderService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("order_broken_link:"))
async def broken_link_callback(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Handle 'Link not working' inline button."""
    order_id = int(callback.data.split(":")[1])

    if user is None:
        logger.warning(f"Unauthorized broken_link attempt: user_id={callback.from_user.id}, order_id={order_id}, reason=user_not_found")
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    order_service = OrderService(session, EncryptionService(app_settings.ENCRYPTION_KEY))
    order = await order_service.get_order_by_id(order_id)

    if order is None:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if order.user_id != user.id:
        logger.warning(f"Unauthorized broken_link attempt: user_id={callback.from_user.id}, order_id={order_id}, owner_id={order.user_id}")
        await callback.answer("Это не ваша заявка.", show_alert=True)
        return

    await order_service.mark_link_broken(order_id)

    notif_service = NotificationService(session)
    bot = callback.bot
    await notif_service.notify_broken_link(bot, order, user)

    await callback.answer("Мы уже меняем ссылку. Новая ссылка будет отправлена сюда же.", show_alert=True)
    logger.info(f"Broken link reported for order #{order_id} by user {user.telegram_id}")
