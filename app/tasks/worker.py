"""ARQ worker configuration."""

from arq import RedisSettings
from arq.connections import create_pool

from app.config import settings
from app.tasks.jobs import send_notification, update_broken_links


def arq_redis_settings() -> RedisSettings:
    """Parse ARQ Redis URL into RedisSettings."""
    url = settings.ARQ_REDIS_URL
    parts = url.replace("redis://", "").split(":")
    host = parts[0] if parts else "localhost"
    port_db = parts[1] if len(parts) > 1 else "6379/1"
    port, db = port_db.split("/") if "/" in port_db else (port_db, 1)
    return RedisSettings(
        host=host,
        port=int(port),
        database=int(db),
    )


class WorkerSettings:
    """ARQ WorkerSettings class — entry point for arq worker."""
    functions = [send_notification, update_broken_links]
    redis_settings = arq_redis_settings()
    max_tries = 3

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Startup hook — create Redis connection pool."""
        import logging
        logging.getLogger(__name__).info("ARQ worker starting up")

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Shutdown hook."""
        import logging
        logging.getLogger(__name__).info("ARQ worker shutting down")

    @staticmethod
    async def on_job_start(ctx: dict, job_id: str) -> None:
        """Job start hook."""
        import logging
        logging.getLogger(__name__).info(f"ARQ job {job_id} started")
