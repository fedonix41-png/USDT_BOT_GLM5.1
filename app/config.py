from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str  # 64-char hex = 32 bytes AES-256
    SUPER_ADMIN_TELEGRAM_ID: int

    # Pagination
    ORDERS_PER_PAGE: int = 5

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379/1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
