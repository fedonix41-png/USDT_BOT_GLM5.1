"""Notification chat repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.notification_chat import NotificationChat
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[NotificationChat]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationChat, session)

    async def get_all_chats(self) -> list[NotificationChat]:
        stmt = select(NotificationChat).order_by(NotificationChat.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_chat_id(self, chat_id: int) -> NotificationChat | None:
        stmt = select(NotificationChat).where(NotificationChat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_chat(self, chat_id: int, added_by: int) -> NotificationChat:
        return await self.create(chat_id=chat_id, added_by=added_by)

    async def remove_chat(self, chat_id: int) -> bool:
        chat = await self.get_by_chat_id(chat_id)
        if chat is None:
            return False
        await self.session.delete(chat)
        await self.session.flush()
        return True
