"""Callback data factories for aiogram."""

from aiogram.filters.callback_data import CallbackData


class OrderAction(CallbackData, prefix="order"):
    """Callback data for order actions (cancel, complete, etc)."""
    action: str
    order_id: int


class Pagination(CallbackData, prefix="page"):
    """Callback data for pagination."""
    list_type: str
    offset: int


class LinkAction(CallbackData, prefix="link"):
    """Callback data for link actions."""
    action: str
    type: str  # buy or sell


class NotificationAction(CallbackData, prefix="notif"):
    """Callback data for notification chat actions."""
    action: str
    chat_id: int | None = None


class ManagementAction(CallbackData, prefix="mgmt"):
    """Callback data for admin management menu."""
    action: str


class CalendarAction(CallbackData, prefix="cal"):
    """Callback data for calendar widget."""
    action: str
    year: int | None = None
    month: int | None = None
    day: int | None = None
    prefix: str = "cal"
