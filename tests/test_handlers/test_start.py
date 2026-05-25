"""Tests for /start handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.models.user import RoleEnum


class TestStartHandler:
    """Basic tests for the /start handler logic."""

    def test_role_enum_values(self):
        """Verify RoleEnum has all expected values."""
        assert RoleEnum.super_admin.value == "super_admin"
        assert RoleEnum.admin.value == "admin"
        assert RoleEnum.operator.value == "operator"
        assert RoleEnum.client.value == "client"

    def test_role_display_name(self):
        """Verify role display name mapping."""
        from app.utils.formatting import role_display_name
        assert role_display_name("super_admin") == "Суперадмин"
        assert role_display_name("admin") == "Администратор"
        assert role_display_name("operator") == "Оператор"
        assert role_display_name("client") == "Клиент"

    def test_format_rates(self):
        """Verify rate formatting."""
        from app.utils.formatting import format_rates
        text = format_rates("95.50", "96.00")
        assert "95.50" in text
        assert "96.00" in text

    def test_format_rates_not_set(self):
        """Verify rate formatting when rates not set."""
        from app.utils.formatting import format_rates
        text = format_rates(None, None)
        assert "Не установлен" in text

    def test_format_statistics(self):
        """Verify statistics formatting."""
        from app.utils.formatting import format_statistics
        from datetime import datetime
        stats = {
            "count_buy": 5,
            "sum_buy": 500.0,
            "count_sell": 3,
            "sum_sell": 300.0,
            "total": 8,
        }
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        text = format_statistics(stats, start, end)
        assert "5" in text
        assert "500.0" in text
        assert "8" in text
