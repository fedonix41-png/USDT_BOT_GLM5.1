"""Entry point for the USDT Exchange Telegram Bot."""

import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher

from app.bot import setup_bot, setup_dispatcher, set_miniapp_menu_button
from app.database.engine import engine
from app.health import start_health_server
from app.utils.logging_config import setup_logging
from app.utils.redis import close_redis

setup_logging()

logger = logging.getLogger(__name__)


class GracefulShutdown:
    _instance = None

    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None

    @classmethod
    def get_instance(cls) -> "GracefulShutdown":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def setup_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: self._signal_handler(s))
            except NotImplementedError:
                signal.signal(sig, lambda s, f: self._signal_handler(s))

    def _signal_handler(self, sig: signal.Signals) -> None:
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def shutdown(self) -> None:
        if self.dp:
            await self.dp.stop_polling()
        if self.bot:
            await self.bot.session.close()
        await engine.dispose()
        await close_redis()
        logger.info("Graceful shutdown completed.")


async def main() -> None:
    shutdown = GracefulShutdown.get_instance()
    shutdown.bot = setup_bot()
    shutdown.dp = setup_dispatcher()

    # Set Mini App menu button
    await set_miniapp_menu_button(shutdown.bot)

    shutdown.setup_signal_handlers()

    await start_health_server()
    logger.info("Starting USDT Exchange Bot (Long Polling)...")

    try:
        await shutdown.dp.start_polling(
            shutdown.bot,
            allowed_updates=shutdown.dp.resolve_used_update_types(),
        )
    except Exception as e:
        logger.exception(f"Unexpected error during polling: {e}")
    finally:
        await shutdown.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
