"""ARQ worker configuration."""

from arq.connections import RedisSettings

from app.config import settings
from app.tasks.jobs import send_notification, update_broken_links


def arq_redis_settings() -> RedisSettings:
    """Parse ARQ Redis URL into RedisSettings."""
    return RedisSettings.from_dsn(settings.ARQ_REDIS_URL)


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
