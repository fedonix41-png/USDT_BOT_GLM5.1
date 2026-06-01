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

    async def send_to_all_chats(self, bot: Bot, text: str, reply_markup=None) -> list[bool]:
        chats = await self._get_all_chats()
        results = []
        
        chat_ids = {chat.chat_id for chat in chats}
        
        # Add super admin for easy testing and debugging
        from app.config import settings as app_settings
        if app_settings.SUPER_ADMIN_TELEGRAM_ID:
            chat_ids.add(app_settings.SUPER_ADMIN_TELEGRAM_ID)
            
        # Add all operators, admins, and super admins from the DB so they receive direct DM notifications too
        from sqlalchemy import select
        from app.database.models.user import User, RoleEnum
        try:
            stmt = select(User).where(User.role.in_([RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin]))
            res = await self.session.execute(stmt)
            staff_users = res.scalars().all()
            for staff in staff_users:
                if staff.telegram_id:
                    chat_ids.add(staff.telegram_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to fetch staff users for direct notifications: {e}")
            
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
                results.append(True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Failed to send notification to chat {chat_id}: {e}"
                )
                results.append(False)
        return results

    async def notify_new_order(self, bot: Bot, order: Order, user: User) -> None:
        from app.config import settings as app_settings
        from app.services.encryption import EncryptionService
        from app.keyboards.inline_kb import order_operator_kb

        order_type_str = "Покупка" if order.order_type.value == "buy" else "Продажа"
        if user.username:
            client_info = f"@{user.username}"
        elif user.phone:
            client_info = f"📱 {user.phone}"
        else:
            client_info = f"ID: {user.telegram_id}"

        details_str = ""
        if order.payment_link_snapshot:
            try:
                encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
                decrypted = encryption.decrypt(order.payment_link_snapshot)
                if decrypted:
                    details_str = f"\nРеквизиты: {decrypted}"
            except Exception:
                pass

        text = (
            f"🆕 Новая заявка #{order.id}\n"
            f"Тип: {order_type_str}\n"
            f"Клиент: {client_info} (ID: {user.telegram_id})\n"
            f"Сумма: {order.amount_usdt} USDT\n"
            f"К оплате: {order.total_fiat} RUB"
            f"{details_str}"
        )
        kb = order_operator_kb(order.id)
        await self.send_to_all_chats(bot, text, reply_markup=kb)

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

    async def notify_role_demoted(self, bot: Bot, user: User, former_role: str) -> None:
        text = f"👤 У пользователя @{user.username or 'N/A'} (ID: {user.telegram_id}) снята роль {former_role}"
        await self.send_to_all_chats(bot, text)

    async def notify_user_banned(self, bot: Bot, user: User, banned: bool) -> None:
        action = "заблокирован" if banned else "разблокирован"
        emoji = "🚫" if banned else "✅"
        client_info = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
        text = f"{emoji} Пользователь {client_info} {action}"
        await self.send_to_all_chats(bot, text)

    async def add_chat(self, chat_id: int, added_by: int) -> NotificationChat:
        return await self.notif_repo.add_chat(chat_id=chat_id, added_by=added_by)

    async def remove_chat(self, chat_id: int) -> bool:
        return await self.notif_repo.remove_chat(chat_id)

    async def get_all_chats(self) -> list[NotificationChat]:
        return await self.notif_repo.get_all_chats()

    async def get_by_chat_id(self, chat_id: int) -> NotificationChat | None:
        return await self.notif_repo.get_by_chat_id(chat_id)
