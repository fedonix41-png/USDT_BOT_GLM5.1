"""Entry point for the USDT Exchange Bot and REST API (FastAPI)."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Request

from app.api.app import create_api_app
from app.bot import set_miniapp_menu_button, setup_bot, setup_dispatcher
from app.config import settings
from app.database.engine import engine
from app.utils.logging_config import setup_logging
from app.utils.redis import close_redis

setup_logging()
logger = logging.getLogger(__name__)

bot = setup_bot()
dp = setup_dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Setting up webhook...")
    base_url = settings.WEBHOOK_URL.rstrip("/")
    webhook_url = f"{base_url}{settings.WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )
    logger.info(f"Webhook set to {webhook_url}")

    # Set Mini App menu button
    await set_miniapp_menu_button(bot)
    
    # Trigger aiogram startup events
    await dp.emit_startup(bot=bot)
    
    yield
    
    logger.info("Deleting webhook...")
    await dp.emit_shutdown(bot=bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
    await engine.dispose()
    await close_redis()
    logger.info("Graceful shutdown completed.")

app = create_api_app()
app.router.lifespan_context = lifespan

@app.post(settings.WEBHOOK_PATH)
async def bot_webhook(request: Request):
    """Telegram Webhook handler."""
    try:
        update_data = await request.json()
        update = Update(**update_data)
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.error(f"Error handling Telegram webhook update: {e}", exc_info=True)
    return {"ok": True}

if __name__ == "__main__":
    # Start uvicorn server
    port = settings.HEALTH_PORT if settings.HEALTH_PORT else 8080
    uvicorn.run(app, host="0.0.0.0", port=port)
