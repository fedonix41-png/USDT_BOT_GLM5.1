"""Healthcheck HTTP server for Docker monitoring."""

import json
import logging

from aiohttp import web

from app.config import settings
from app.database.engine import engine
from app.utils.redis import get_redis

logger = logging.getLogger(__name__)


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint — verifies DB and Redis connectivity."""
    checks = {"database": False, "redis": False}

    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"Health check DB failed: {e}")

    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Health check Redis failed: {e}")

    all_healthy = all(checks.values())
    status = 200 if all_healthy else 503

    return web.Response(
        status=status,
        content_type="application/json",
        body=json.dumps({"status": "healthy" if all_healthy else "unhealthy", "checks": checks}),
    )


async def readiness_check(request: web.Request) -> web.Response:
    """Readiness probe — same as health for now."""
    return await health_check(request)


async def liveness_check(request: web.Request) -> web.Response:
    """Liveness probe — always returns 200 if the process is alive."""
    return web.Response(
        status=200,
        content_type="application/json",
        body=json.dumps({"status": "alive"}),
    )


def create_health_app() -> web.Application:
    """Create aiohttp application for health checks."""
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/ready", readiness_check)
    app.router.add_get("/live", liveness_check)
    return app


async def start_health_server(port: int | None = None) -> None:
    """Start health check HTTP server."""
    app = create_health_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port or settings.HEALTH_PORT)
    await site.start()
    logger.info(f"Health check server started on port {port or settings.HEALTH_PORT}")
