from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class APIToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    user = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_api_tokens_user_id", "user_id"),
        Index("ix_api_tokens_jti", "jti"),
    )

    def __repr__(self) -> str:
        return f"<APIToken id={self.id} user_id={self.user_id} jti={self.jti[:8]}...>"
