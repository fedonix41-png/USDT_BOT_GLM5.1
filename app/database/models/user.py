import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RoleEnum(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    operator = "operator"
    client = "client"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="user_role"), default=RoleEnum.client, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    orders = relationship("Order", back_populates="user", lazy="selectin")
    rates_set = relationship("Rate", back_populates="set_by_user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} role={self.role}>"
