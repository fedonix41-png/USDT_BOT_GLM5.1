"""Bot instance and Dispatcher setup with router registration."""

import logging

from aiogram import Bot, Dispatcher

from app.config import settings
from app.handlers.admin import change_links, change_rate, assign_roles, notification_chats, toggle_flags
from app.handlers.client import buy, cancel_order, rates, sell, support
from app.handlers.common import broken_link, cancel, calendar
from app.handlers.operator import active_orders, complete_order, statistics
from app.handlers.start import router as start_router
from app.middlewares.bot_status import BotStatusMiddleware
from app.middlewares.db_session import DBSessionMiddleware
from app.middlewares.role_guard import RoleGuardMiddleware
from app.middlewares.user_middleware import UserMiddleware

logger = logging.getLogger(__name__)


def setup_bot() -> Bot:
    """Create and return Bot instance."""
    bot = Bot(token=settings.BOT_TOKEN)
    return bot


def setup_dispatcher() -> Dispatcher:
    """Create Dispatcher, register routers and middlewares."""
    dp = Dispatcher()

    # Register middlewares — ORDER MATTERS!
    # Last registered = outermost (wraps everything).
    # Execution order: DBSession → User → BotStatus → RoleGuard → handler
    dp.message.middleware(RoleGuardMiddleware())
    dp.callback_query.middleware(RoleGuardMiddleware())

    dp.message.middleware(BotStatusMiddleware())
    dp.callback_query.middleware(BotStatusMiddleware())

    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())

    # Register routers — ORDER MATTERS for cancel handler!
    # Cancel handler must be registered BEFORE specific FSM handlers
    # so it catches "❌ Отмена" across all states.
    dp.include_router(cancel.router)
    dp.include_router(calendar.router)

    dp.include_router(start_router)

    # Client handlers
    dp.include_router(buy.router)
    dp.include_router(sell.router)
    dp.include_router(rates.router)
    dp.include_router(cancel_order.router)
    dp.include_router(support.router)

    # Common handlers
    dp.include_router(broken_link.router)

    # Operator handlers
    dp.include_router(active_orders.router)
    dp.include_router(complete_order.router)
    dp.include_router(statistics.router)

    # Admin handlers
    dp.include_router(change_rate.router)
    dp.include_router(change_links.router)
    dp.include_router(toggle_flags.router)
    dp.include_router(notification_chats.router)
    dp.include_router(assign_roles.router)

    logger.info("Dispatcher configured with all routers and middlewares")
    return dp
