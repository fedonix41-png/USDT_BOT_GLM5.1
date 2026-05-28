from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str
    SUPER_ADMIN_TELEGRAM_ID: int

    # Pagination
    ORDERS_PER_PAGE: int = 5

    # Web App
    WEBAPP_URL: str = "https://example.com"

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379/1"

    # Logging
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False

    # Healthcheck
    HEALTH_PORT: int = 8080

    # API
    API_SECRET_KEY: str = ""
    API_ACCESS_TOKEN_EXPIRE: int = 30 * 60
    API_REFRESH_TOKEN_EXPIRE: int = 7 * 24 * 60 * 60
    API_PORT: int = 8081
    API_RATE_LIMIT: int = 100
    API_CORS_ORIGINS: list[str] = []
    API_ADMIN_IP_WHITELIST: list[str] = []
    API_LOGIN_BLOCK_DURATION: int = 5 * 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
