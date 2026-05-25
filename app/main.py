"""Entry point for the USDT Exchange Telegram Bot."""

import asyncio
import logging

from app.bot import setup_bot, setup_dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the bot with long polling."""
    bot = setup_bot()
    dp = setup_dispatcher()

    logger.info("Starting USDT Exchange Bot (Long Polling)...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
