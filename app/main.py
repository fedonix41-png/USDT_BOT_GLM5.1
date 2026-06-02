"""Entry point for the USDT Exchange Telegram Bot."""

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.bot import setup_bot, setup_dispatcher, set_miniapp_menu_button
from app.config import settings
from app.database.engine import engine
from app.health import create_health_app
from app.utils.logging_config import setup_logging
from app.utils.redis import close_redis

setup_logging()

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    logger.info("Setting up webhook...")
    base_url = settings.WEBHOOK_URL.rstrip("/")
    webhook_url = f"{base_url}{settings.WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dispatcher.resolve_used_update_types(),
        drop_pending_updates=True
    )
    logger.info(f"Webhook set to {webhook_url}")

    # Set Mini App menu button
    await set_miniapp_menu_button(bot)


async def on_shutdown(bot: Bot, dispatcher: Dispatcher) -> None:
    logger.info("Deleting webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
    await engine.dispose()
    await close_redis()
    logger.info("Graceful shutdown completed.")


def main() -> None:
    bot = setup_bot()
    dp = setup_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = create_health_app()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=settings.WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    logger.info(f"Starting USDT Exchange Bot (Webhook on port {settings.HEALTH_PORT})...")
    web.run_app(app, host="0.0.0.0", port=settings.HEALTH_PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
