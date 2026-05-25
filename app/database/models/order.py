import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class OrderTypeEnum(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderStatusEnum(str, enum.Enum):
    created = "created"
    cancelled = "cancelled"
    completed = "completed"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_type: Mapped[OrderTypeEnum] = mapped_column(Enum(OrderTypeEnum, name="order_type"), nullable=False)
    amount_usdt: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum, name="order_status"), default=OrderStatusEnum.created, nullable=False
    )
    payment_link_snapshot: Mapped[str | None] = mapped_column(Text)
    link_broken: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message_id: Mapped[int | None] = mapped_column(Integer)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="orders", lazy="selectin")

    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_type_created", "order_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} type={self.order_type} status={self.status} amount={self.amount_usdt}>"
