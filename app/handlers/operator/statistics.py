"""Handler for statistics over a period — inline calendar date picker.

Uses the calendar_kb inline keyboard for date selection instead of text input.
FSM StatisticsStates manages the two-step flow: start date → end date.
"""

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.fsm.statistics_states import StatisticsStates
from app.keyboards.calendar_kb import calendar_kb
from app.keyboards.cancel_kb import cancel_keyboard

logger = logging.getLogger(__name__)

router = Router()

_CALENDAR_PREFIX = "cal"


@router.message(F.text == "📈 Статистика", StateFilter(None))
async def start_statistics(message: Message, state: FSMContext) -> None:
    """Initiate statistics FSM — show inline calendar for start date."""
    await state.set_state(StatisticsStates.waiting_start_date)

    kb = calendar_kb(prefix=_CALENDAR_PREFIX)
    await message.answer(
        "Выберите начальную дату:",
        reply_markup=cancel_keyboard(),
    )
    # Calendar is a separate message with inline keyboard
    await message.answer("📅 Календарь:", reply_markup=kb)
