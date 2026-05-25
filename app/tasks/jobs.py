"""ARQ background task functions."""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from arq import Retry

from app.config import settings as app_settings
from app.database.engine import async_session_maker
from app.database.models.order import OrderStatusEnum, OrderTypeEnum
from app.repositories.notification_repo import NotificationRepository
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def _deactivate_chat_and_notify_admin(chat_id: int, reason: str) -> None:
    """Deactivate notification chat and notify super admin."""
    async with async_session_maker() as session:
        notif_repo = NotificationRepository(session)
        deactivated = await notif_repo.deactivate_chat(chat_id)
        if deactivated:
            logger.warning(f"Deactivated notification chat {chat_id}: {reason}")
            try:
                bot = Bot(token=app_settings.BOT_TOKEN)
                await bot.send_message(
                    chat_id=app_settings.SUPER_ADMIN_TELEGRAM_ID,
                    text=f"⚠️ Чат уведомлений {chat_id} деактивирован.\nПричина: {reason}",
                )
                await bot.session.close()
            except Exception as e:
                logger.error(f"Failed to notify super admin about deactivation: {e}")
        await session.commit()


async def send_notification(ctx: dict, chat_ids: list[int], text: str) -> list[bool]:
    """Send notification message to all specified chat IDs.

    Args:
        ctx: ARQ context with 'job_try' for retry count.
        chat_ids: List of chat IDs to send notification to.
        text: Message text to send.

    Returns:
        List of success flags for each chat.
    """
    bot = Bot(token=app_settings.BOT_TOKEN)
    results = []
    current_try = ctx.get("job_try", 1)

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            results.append(True)
        except TelegramForbiddenError as e:
            logger.error(f"Bot blocked by chat {chat_id}: {e}")
            await _deactivate_chat_and_notify_admin(chat_id, "Бот заблокирован пользователем")
            results.append(False)
        except TelegramNotFound as e:
            logger.error(f"Chat {chat_id} not found: {e}")
            await _deactivate_chat_and_notify_admin(chat_id, "Чат не найден")
            results.append(False)
        except Exception as e:
            logger.error(f"Failed to send notification to chat {chat_id}: {e}")
            if current_try >= MAX_RETRIES:
                await _deactivate_chat_and_notify_admin(chat_id, f"Не удалось доставить после {MAX_RETRIES} попыток")
                results.append(False)
            else:
                await bot.session.close()
                raise Retry(defer=5)

    await bot.session.close()
    return results


async def update_broken_links(ctx: dict, order_type: str) -> int:
    """Find all orders with broken links and update their messages with new payment link.

    Args:
        ctx: ARQ context.
        order_type: 'buy' or 'sell'.

    Returns:
        Number of updated orders.
    """
    bot = Bot(token=app_settings.BOT_TOKEN)
    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    count = 0

    async with async_session_maker() as session:
        try:
            order_type_enum = OrderTypeEnum(order_type)
            settings_service = SettingsService(session, encryption)
            new_link = await settings_service.get_payment_link(order_type_enum)

            if not new_link:
                logger.warning(f"No payment link set for {order_type}")
                await bot.session.close()
                return 0

            order_service = OrderService(session, encryption)
            broken_orders = await order_service.get_broken_link_orders(order_type_enum)
            user_service = UserService(session)

            from app.keyboards.inline_kb import order_client_kb
            from app.utils.formatting import format_order_message

            for order in broken_orders:
                if order.status != OrderStatusEnum.created:
                    continue

                if order.chat_id and order.message_id:
                    try:
                        user = await user_service.get_by_telegram_id(
                            order.user.telegram_id if order.user else 0
                        )
                        text = format_order_message(order, user, new_link)
                        kb = order_client_kb(order.id)
                        await bot.edit_message_text(
                            chat_id=order.chat_id,
                            message_id=order.message_id,
                            text=text,
                            reply_markup=kb,
                        )

                        await bot.send_message(
                            chat_id=order.chat_id,
                            text="🔗 Ссылка обновлена. Актуальные реквизиты выше.",
                        )

                        order.link_broken = False
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to update broken link for order #{order.id}: {e}")

            await session.commit()
        except Exception as e:
            logger.error(f"Error in update_broken_links task: {e}")
            await session.rollback()

    await bot.session.close()
    logger.info(f"Updated {count} broken link orders for {order_type}")
    return count
