import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, CallbackQuery

from app.middlewares.bot_status import BotStatusMiddleware
from app.database.models.user import User, RoleEnum


@pytest.mark.asyncio
async def test_redis_failure_blocks_client(session, sample_user):
    """
    При ошибке Redis клиенты видят "Бот временно недоступен."
    """
    # 1. Создаём мок для Redis который выбрасывает исключение
    with patch("app.middlewares.bot_status.get_cached_flag", side_effect=ConnectionError("Redis unavailable")):
        middleware = BotStatusMiddleware()
        
        # Мок Message с client-пользователем
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        
        # 3. Вызываем middleware
        result = await middleware(
            handler=AsyncMock(return_value="should_not_reach"),
            event=message,
            data={"session": session, "user": sample_user}  # client role
        )
        
        # 4. Проверяем что клиент получил сообщение о недоступности
        message.answer.assert_awaited_once_with("Бот временно недоступен.")
        assert result is None  # handler не был вызван


@pytest.mark.asyncio
async def test_redis_failure_allows_admin(session, admin_user):
    """
    Admin/Operator проходят даже при недоступности Redis.
    """
    with patch("app.middlewares.bot_status.get_cached_flag", side_effect=ConnectionError("Redis unavailable")):
        middleware = BotStatusMiddleware()
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        
        result = await middleware(
            handler=AsyncMock(return_value="success"),
            event=message,
            data={"session": session, "user": admin_user}  # admin role
        )
        
        # Admin проходит без проверки Redis
        assert result == "success"
        message.answer.assert_not_awaited()
