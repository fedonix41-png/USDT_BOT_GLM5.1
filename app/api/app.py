"""REST API application entry point."""

import asyncio
import logging
import signal

from aiohttp import web

from app.api.deps import auth_middleware
from app.api.exceptions import api_error_middleware
from app.api.middleware import (
    cors_middleware,
    ip_whitelist_middleware,
    logging_middleware,
    login_rate_limit_middleware,
    rate_limit_middleware,
)
from app.api.routers import auth, orders, rates, settings, statistics, users
from app.config import settings as app_settings
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def create_api_app() -> web.Application:
    app = web.Application(
        middlewares=[
            logging_middleware,
            cors_middleware,
            rate_limit_middleware,
            login_rate_limit_middleware,
            auth_middleware,
            ip_whitelist_middleware,
            api_error_middleware,
        ]
    )

    app["logger"] = logger

    app.router.add_routes(auth.router)
    app.router.add_routes(users.router)
    app.router.add_routes(orders.router)
    app.router.add_routes(rates.router)
    app.router.add_routes(settings.router)
    app.router.add_routes(statistics.router)
    
    from app.api.routers import telegram
    app.router.add_routes(telegram.router)

    async def health_check(request: web.Request) -> web.Response:
        return web.json_response({"status": "healthy"})

    app.router.add_get("/api/v1/health", health_check)

    logger.info("API application created")
    return app


async def start_api_server(port: int | None = None) -> None:
    setup_logging()
    app = create_api_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port or app_settings.API_PORT)

    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    await site.start()
    logger.info(f"API server started on port {port or app_settings.API_PORT}")

    try:
        await shutdown_event.wait()
    finally:
        logger.info("Shutting down API server...")
        await runner.cleanup()
        logger.info("API server stopped")


if __name__ == "__main__":
    asyncio.run(start_api_server())
