"""Calendar callback handlers for inline date selection.

Works with the calendar_kb from app.keyboards.calendar_kb.
Used by the statistics handler for selecting start/end dates.

Callback data patterns:
  cal:nav:prev:{year}:{month}   — navigate to previous month
  cal:nav:next:{year}:{month}   — navigate to next month
  cal:pick:{year}:{month}:{day} — select a day
  cal:ignore                     — no-op placeholder
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.fsm.statistics_states import StatisticsStates
from app.keyboards.calendar_kb import calendar_kb
from app.keyboards.cancel_kb import get_main_keyboard
from app.services.order_service import OrderService
from app.utils.formatting import format_statistics
from app.utils.helpers import get_settings_flags

logger = logging.getLogger(__name__)

router = Router()

# Prefix used for calendar callback data
_CALENDAR_PREFIX = "cal"


@router.callback_query(F.data == f"{_CALENDAR_PREFIX}:ignore")
async def ignore_calendar_button(callback: CallbackQuery) -> None:
    """Ignore clicks on header/placeholder buttons."""
    await callback.answer()


@router.callback_query(F.data.startswith(f"{_CALENDAR_PREFIX}:nav:"))
async def navigate_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle month navigation in the calendar."""
    parts = callback.data.split(":")
    # cal:nav:direction:year:month
    target_year = int(parts[3])
    target_month = int(parts[4])

    new_kb = calendar_kb(year=target_year, month=target_month, prefix=_CALENDAR_PREFIX)

    try:
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass  # Message not modified or other Telegram API error

    await callback.answer()


@router.callback_query(F.data.startswith(f"{_CALENDAR_PREFIX}:pick:"))
async def pick_calendar_date(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Handle day selection in the calendar."""
    parts = callback.data.split(":")
    # cal:pick:year:month:day
    year = int(parts[2])
    month = int(parts[3])
    day = int(parts[4])
    selected_date = datetime(year, month, day)

    current_state = await state.get_state()

    if current_state == StatisticsStates.waiting_start_date:
        # Save start date and ask for end date
        await state.update_data(start_date=selected_date)
        await state.set_state(StatisticsStates.waiting_end_date)

        new_kb = calendar_kb(prefix=_CALENDAR_PREFIX)
        await callback.message.edit_text(
            text=(
                f"✅ Начальная дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
                f"Теперь выберите конечную дату:"
            ),
            reply_markup=new_kb,
        )
        await callback.answer(f"Выбрана дата: {selected_date.strftime('%d.%m.%Y')}")

    elif current_state == StatisticsStates.waiting_end_date:
        # Validate and show statistics
        data = await state.get_data()
        start_date: datetime = data["start_date"]

        if selected_date < start_date:
            await callback.answer(
                "Конечная дата должна быть ≥ начальной!",
                show_alert=True,
            )
            return

        end_date = selected_date.replace(hour=23, minute=59, second=59)

        # Fetch statistics (encryption=None — get_statistics doesn't need it)
        order_service = OrderService(session, None)  # type: ignore[arg-type]
        stats = await order_service.get_statistics(start_date, end_date)

        text = format_statistics(stats, start_date, end_date)

        # Restore main menu keyboard
        if user is not None:
            flags = await get_settings_flags(session)
            kb = get_main_keyboard(
                role=user.role,
                buy_enabled=flags["buy_enabled"],
                sell_enabled=flags["sell_enabled"],
                bot_enabled=flags["bot_enabled"],
                is_super_admin=user.role == RoleEnum.super_admin,
            )
        else:
            kb = None

        await callback.message.edit_text(text)
        if kb:
            await callback.message.answer("Выберите действие:", reply_markup=kb)

        await state.clear()
        logger.info(f"Statistics shown for {start_date} - {end_date}")
        await callback.answer()

    else:
        await callback.answer("Выбор даты не актуален.", show_alert=True)
