"""Tests for service classes."""

import pytest
import pytest_asyncio
from decimal import Decimal

from app.database.models.order import OrderStatusEnum, OrderTypeEnum
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum
from app.repositories.audit_repo import AuditRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.rate_repo import RateRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.audit_service import AuditService
from app.services.order_service import OrderService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService


class TestUserService:
    async def test_get_or_create_new_user(self, session):
        svc = UserService(session)
        # Temporarily override SUPER_ADMIN_TELEGRAM_ID
        import app.config as cfg
        original = cfg.settings.SUPER_ADMIN_TELEGRAM_ID
        cfg.settings.SUPER_ADMIN_TELEGRAM_ID = -1

        user = await svc.get_or_create(12345, "testuser", "Test User")
        assert user.telegram_id == 12345
        assert user.role == RoleEnum.client

        cfg.settings.SUPER_ADMIN_TELEGRAM_ID = original

    async def test_get_or_create_super_admin(self, session):
        svc = UserService(session)
        import app.config as cfg
        original = cfg.settings.SUPER_ADMIN_TELEGRAM_ID
        cfg.settings.SUPER_ADMIN_TELEGRAM_ID = 99999

        user = await svc.get_or_create(99999, "superadmin", "Super Admin")
        assert user.role == RoleEnum.super_admin

        cfg.settings.SUPER_ADMIN_TELEGRAM_ID = original

    async def test_get_or_create_existing_user(self, session):
        svc = UserService(session)
        user1 = await svc.get_or_create(12345, "testuser", "Test User")
        user2 = await svc.get_or_create(12345, "updated", "Updated Name")
        assert user1.id == user2.id
        assert user2.username == "updated"

    async def test_set_role(self, session, sample_user, admin_user):
        svc = UserService(session)
        updated = await svc.set_role(sample_user.id, RoleEnum.operator, admin_user.id)
        assert updated.role == RoleEnum.operator

    async def test_get_by_telegram_id(self, session, sample_user):
        svc = UserService(session)
        found = await svc.get_by_telegram_id(sample_user.telegram_id)
        assert found is not None
        assert found.id == sample_user.id

    async def test_get_by_telegram_id_not_found(self, session):
        svc = UserService(session)
        found = await svc.get_by_telegram_id(999999999)
        assert found is None


class TestRateService:
    async def test_set_and_get_rate(self, session, admin_user):
        svc = RateService(session)
        await svc.set_rate(RateTypeEnum.buy, Decimal("95.50"), admin_user.id)
        rate = await svc.get_current_rate(RateTypeEnum.buy)
        assert rate == Decimal("95.50")

    async def test_get_rate_none_when_not_set(self, session):
        svc = RateService(session)
        rate = await svc.get_current_rate(RateTypeEnum.buy)
        assert rate is None

    async def test_rate_history(self, session, admin_user):
        svc = RateService(session)
        await svc.set_rate(RateTypeEnum.sell, Decimal("96.00"), admin_user.id)
        await svc.set_rate(RateTypeEnum.sell, Decimal("96.50"), admin_user.id)
        history = await svc.get_rate_history(RateTypeEnum.sell, limit=10)
        assert len(history) == 2
        # Most recent first
        assert history[0].value == Decimal("96.50")


class TestSettingsService:
    async def test_get_set_flag(self, session, encryption_service, admin_user):
        svc = SettingsService(session, encryption_service)
        assert await svc.is_bot_enabled() is True  # Default

        await svc.set("bot_enabled", "0", user_id=admin_user.id)
        assert await svc.is_bot_enabled() is False

    async def test_payment_link_encrypt_decrypt(self, session, encryption_service, admin_user):
        svc = SettingsService(session, encryption_service)
        link = "https://pay.example.com/12345"
        await svc.set_payment_link(OrderTypeEnum.buy, link, admin_user.id)
        retrieved = await svc.get_payment_link(OrderTypeEnum.buy)
        assert retrieved == link

    async def test_toggle_flag(self, session, encryption_service, admin_user):
        svc = SettingsService(session, encryption_service)
        # Default is enabled
        now_enabled = await svc.toggle_flag("buy_enabled", admin_user.id)
        assert now_enabled is False  # Was True, now False
        now_enabled = await svc.toggle_flag("buy_enabled", admin_user.id)
        assert now_enabled is True  # Was False, now True


class TestOrderService:
    async def test_create_order(self, session, encryption_service, sample_user):
        svc = OrderService(session, encryption_service)
        order = await svc.create_order(
            user_id=sample_user.id,
            order_type=OrderTypeEnum.buy,
            amount_usdt=Decimal("100"),
            rate=Decimal("95.50"),
            payment_link="https://pay.example.com",
            message_id=42,
            chat_id=111222333,
        )
        assert order.id is not None
        assert order.amount_usdt == Decimal("100")
        assert order.total_fiat == Decimal("9550.00")
        assert order.status == OrderStatusEnum.created

    async def test_cancel_order(self, session, encryption_service, sample_user):
        svc = OrderService(session, encryption_service)
        order = await svc.create_order(
            user_id=sample_user.id,
            order_type=OrderTypeEnum.buy,
            amount_usdt=Decimal("50"),
            rate=Decimal("95.00"),
            payment_link="link",
            message_id=1,
            chat_id=111222333,
        )
        cancelled = await svc.cancel_order(order.id, sample_user.id)
        assert cancelled.status == OrderStatusEnum.cancelled

    async def test_complete_order(self, session, encryption_service, sample_user, admin_user):
        svc = OrderService(session, encryption_service)
        order = await svc.create_order(
            user_id=sample_user.id,
            order_type=OrderTypeEnum.buy,
            amount_usdt=Decimal("50"),
            rate=Decimal("95.00"),
            payment_link="link",
            message_id=1,
            chat_id=111222333,
        )
        completed = await svc.complete_order(order.id, admin_user.id)
        assert completed.status == OrderStatusEnum.completed

    async def test_mark_link_broken(self, session, encryption_service, sample_user):
        svc = OrderService(session, encryption_service)
        order = await svc.create_order(
            user_id=sample_user.id,
            order_type=OrderTypeEnum.buy,
            amount_usdt=Decimal("10"),
            rate=Decimal("95.00"),
            payment_link="link",
            message_id=1,
            chat_id=111222333,
        )
        broken = await svc.mark_link_broken(order.id)
        assert broken.link_broken is True

    async def test_cancel_non_created_order_fails(self, session, encryption_service, sample_user):
        svc = OrderService(session, encryption_service)
        order = await svc.create_order(
            user_id=sample_user.id,
            order_type=OrderTypeEnum.buy,
            amount_usdt=Decimal("10"),
            rate=Decimal("95.00"),
            payment_link="link",
            message_id=1,
            chat_id=111222333,
        )
        await svc.cancel_order(order.id, sample_user.id)
        # Try to cancel already cancelled
        result = await svc.cancel_order(order.id, sample_user.id)
        assert result is None


class TestAuditService:
    async def test_log(self, session, sample_user):
        svc = AuditService(session)
        log = await svc.log(
            user_id=sample_user.id,
            action="test_action",
            details={"key": "value"},
        )
        assert log.id is not None
        assert log.action == "test_action"
