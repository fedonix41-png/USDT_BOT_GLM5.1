from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str
    SUPER_ADMIN_TELEGRAM_ID: int

    # Pagination
    ORDERS_PER_PAGE: int = 5

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379/1"

    # Logging
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False

    # Healthcheck
    HEALTH_PORT: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
