"""REST API application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exceptions import setup_exception_handlers
from app.api.middleware import (
    LoggingMiddleware,
    LoginRateLimitMiddleware,
    RateLimitMiddleware,
)
from app.api.routers import auth, exchange, orders, rates, settings, statistics, users, support, telegram
from app.config import settings as app_settings
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

def create_api_app() -> FastAPI:
    setup_logging()
    
    app = FastAPI(
        title="USDT Bot API",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Middlewares (added in reverse order of execution)
    app.add_middleware(LoginRateLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    cors_origins = app_settings.API_CORS_ORIGINS if app_settings.API_CORS_ORIGINS else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=86400,
    )

    # Routers
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(orders.router)
    app.include_router(rates.router)
    app.include_router(settings.router)
    app.include_router(statistics.router)
    app.include_router(exchange.router)
    app.include_router(support.router)
    app.include_router(telegram.router)

    @app.get("/api/v1/health")
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    logger.info("FastAPI application created")
    return app

app = create_api_app()
