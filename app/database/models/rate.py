import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RateTypeEnum(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class Rate(Base):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rate_type: Mapped[RateTypeEnum] = mapped_column(Enum(RateTypeEnum), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    set_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    set_by_user = relationship("User", back_populates="rates_set", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Rate id={self.id} type={self.rate_type} value={self.value}>"
