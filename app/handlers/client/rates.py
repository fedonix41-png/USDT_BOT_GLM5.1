"""Handler for viewing current exchange rates."""

import logging

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import OrderTypeEnum
from app.services.rate_service import RateService
from app.utils.formatting import format_rates

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📊 Курсы")
async def show_rates(message: Message, session: AsyncSession) -> None:
    """Show current buy and sell rates."""
    rate_service = RateService(session)

    buy_rate = await rate_service.get_current_rate(OrderTypeEnum.buy)
    sell_rate = await rate_service.get_current_rate(OrderTypeEnum.sell)

    buy_str = str(buy_rate) if buy_rate else None
    sell_str = str(sell_rate) if sell_rate else None

    text = format_rates(buy_str, sell_str)
    await message.answer(text)
