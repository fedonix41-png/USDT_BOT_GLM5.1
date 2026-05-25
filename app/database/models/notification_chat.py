from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class NotificationChat(Base):
    __tablename__ = "notification_chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    added_by_user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<NotificationChat id={self.id} chat_id={self.chat_id} is_active={self.is_active}>"
