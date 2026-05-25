"""Shared test fixtures."""

# Set test environment variables BEFORE any app imports
# to prevent Settings() from failing at module level in app.config
import os

os.environ.setdefault("BOT_TOKEN", "123456:ABC-test-token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENCRYPTION_KEY", "a" * 64)
os.environ.setdefault("SUPER_ADMIN_TELEGRAM_ID", "100200300")
os.environ.setdefault("ARQ_REDIS_URL", "redis://localhost:6379/1")

import asyncio
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.models import AuditLog, GlobalSettings, NotificationChat, Order, Rate, User
from app.database.models.order import OrderStatusEnum, OrderTypeEnum
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum
from app.services.encryption import EncryptionService

# Test encryption key (64 hex chars = 32 bytes)
TEST_ENCRYPTION_KEY = "a" * 64

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    """Create a fresh database engine for each test."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as sess:
        yield sess


@pytest.fixture
def encryption_service():
    """Create EncryptionService with test key."""
    return EncryptionService(TEST_ENCRYPTION_KEY)


@pytest_asyncio.fixture
async def sample_user(session):
    """Create a sample client user."""
    user = User(
        telegram_id=111222333,
        username="testuser",
        full_name="Test User",
        role=RoleEnum.client,
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(session):
    """Create a sample admin user."""
    user = User(
        telegram_id=999888777,
        username="adminuser",
        full_name="Admin User",
        role=RoleEnum.admin,
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def super_admin_user(session):
    """Create a sample super_admin user."""
    user = User(
        telegram_id=100200300,
        username="superadmin",
        full_name="Super Admin",
        role=RoleEnum.super_admin,
    )
    session.add(user)
    await session.flush()
    return user
