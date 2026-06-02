"""Inline calendar keyboard for date selection in Telegram bots.

Generates a month-grid calendar with navigation arrows.
Callback data is formatted using CalendarAction aiogram CallbackData.
"""

import calendar
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.callback_data import CalendarAction

_MONTH_NAMES_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}

_DAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _month_name(year: int, month: int) -> str:
    """Return 'Месяц Год' in Russian."""
    return f"{_MONTH_NAMES_RU[month]} {year}"


def calendar_kb(
    year: int | None = None,
    month: int | None = None,
    prefix: str = "cal",
) -> InlineKeyboardMarkup:
    """Build an inline calendar keyboard for the given year/month.

    Args:
        year: Year (defaults to current).
        month: Month 1-12 (defaults to current).
        prefix: Callback data prefix to distinguish calendars.

    Returns:
        InlineKeyboardMarkup with month navigation and day grid.
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    buttons: list[list[InlineKeyboardButton]] = []

    # ── Header row: ◀️ Месяц Год ▶️ ──
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    header = [
        InlineKeyboardButton(
            text="◀️",
            callback_data=CalendarAction(prefix=prefix, action="prev", year=prev_year, month=prev_month).pack(),
        ),
        InlineKeyboardButton(
            text=_month_name(year, month),
            callback_data=CalendarAction(prefix=prefix, action="ignore").pack(),
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=CalendarAction(prefix=prefix, action="next", year=next_year, month=next_month).pack(),
        ),
    ]
    buttons.append(header)

    # ── Day-name row ──
    day_name_row = [
        InlineKeyboardButton(text=name, callback_data=CalendarAction(prefix=prefix, action="ignore").pack())
        for name in _DAY_NAMES_RU
    ]
    buttons.append(day_name_row)

    # ── Day grid ──
    cal = calendar.Calendar(firstweekday=0)  # Monday first
    month_days = cal.monthdayscalendar(year, month)

    for week in month_days:
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=CalendarAction(prefix=prefix, action="ignore").pack()))
            else:
                row.append(InlineKeyboardButton(
                    text=str(day),
                    callback_data=CalendarAction(prefix=prefix, action="pick", year=year, month=month, day=day).pack(),
                ))
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
