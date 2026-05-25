"""Handler for statistics over a period — FSM StatisticsStates."""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.fsm.statistics_states import StatisticsStates
from app.services.order_service import OrderService
from app.utils.formatting import format_statistics

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📈 Статистика", StateFilter(None))
async def start_statistics(message: Message, state: FSMContext) -> None:
    """Initiate statistics FSM."""
    await state.set_state(StatisticsStates.waiting_start_date)
    await message.answer("Введите начальную дату (формат: ДД.ММ.ГГГГ):")


@router.message(StatisticsStates.waiting_start_date)
async def process_start_date(message: Message, state: FSMContext) -> None:
    """Process start date input."""
    try:
        start_date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите в формате ДД.ММ.ГГГГ:")
        return

    await state.update_data(start_date=start_date)
    await state.set_state(StatisticsStates.waiting_end_date)
    await message.answer("Введите конечную дату (формат: ДД.ММ.ГГГГ):")


@router.message(StatisticsStates.waiting_end_date)
async def process_end_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process end date input and show statistics."""
    try:
        end_date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите в формате ДД.ММ.ГГГГ:")
        return

    data = await state.get_data()
    start_date = data["start_date"]

    if end_date < start_date:
        await message.answer("Конечная дата должна быть >= начальной. Введите снова:")
        return

    end_date = end_date.replace(hour=23, minute=59, second=59)

    order_service = OrderService(session, None)
    stats = await order_service.get_statistics(start_date, end_date)

    text = format_statistics(stats, start_date, end_date)
    await message.answer(text)
    await state.clear()
    logger.info(f"Statistics shown for {start_date} - {end_date}")
