"""Notification service — send messages to notification chats via ARQ."""

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.notification_chat import NotificationChat
from app.database.models.order import Order
from app.database.models.user import User
from app.repositories.notification_repo import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notif_repo = NotificationRepository(session)

    async def _get_all_chats(self) -> list[NotificationChat]:
        return await self.notif_repo.get_all_chats()

    async def send_to_all_chats(self, bot: Bot, text: str) -> list[bool]:
        chats = await self._get_all_chats()
        results = []
        for chat in chats:
            try:
                await bot.send_message(chat_id=chat.chat_id, text=text)
                results.append(True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Failed to send notification to chat {chat.chat_id}: {e}"
                )
                results.append(False)
        return results

    async def notify_new_order(self, bot: Bot, order: Order, user: User) -> None:
        order_type_str = "Покупка" if order.order_type.value == "buy" else "Продажа"
        text = (
            f"🆕 Новая заявка #{order.id}\n"
            f"Тип: {order_type_str}\n"
            f"Клиент: @{user.username or 'N/A'} (ID: {user.telegram_id})\n"
            f"Сумма: {order.amount_usdt} USDT\n"
            f"К оплате: {order.total_fiat} RUB"
        )
        await self.send_to_all_chats(bot, text)

    async def notify_broken_link(self, bot: Bot, order: Order, user: User) -> None:
        text = (
            f"⚠️ Клиент @{user.username or 'N/A'} жалуется на неработающую ссылку в заявке #{order.id}"
        )
        await self.send_to_all_chats(bot, text)

    async def notify_order_completed(self, bot: Bot, order: Order, operator: User) -> None:
        order_type_str = "покупку" if order.order_type.value == "buy" else "продажу"
        text = (
            f"✅ Заявка #{order.id} на {order_type_str} {order.amount_usdt} USDT завершена\n"
            f"Оператор: @{operator.username or 'N/A'}"
        )
        await self.send_to_all_chats(bot, text)

    async def notify_role_assigned(self, bot: Bot, user: User, role: str) -> None:
        text = f"👤 Пользователю @{user.username or 'N/A'} (ID: {user.telegram_id}) назначена роль {role}"
        await self.send_to_all_chats(bot, text)

    async def add_chat(self, chat_id: int, added_by: int) -> NotificationChat:
        return await self.notif_repo.add_chat(chat_id=chat_id, added_by=added_by)

    async def remove_chat(self, chat_id: int) -> bool:
        return await self.notif_repo.remove_chat(chat_id)

    async def get_all_chats(self) -> list[NotificationChat]:
        return await self.notif_repo.get_all_chats()

    async def get_by_chat_id(self, chat_id: int) -> NotificationChat | None:
        return await self.notif_repo.get_by_chat_id(chat_id)
