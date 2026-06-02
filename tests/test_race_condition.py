import pytest
import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import OrderStatusEnum, OrderTypeEnum
from app.services.order_service import OrderService
from app.services.encryption import EncryptionService


@pytest.mark.asyncio
async def test_race_condition_concurrent_cancel(session, encryption_service, sample_user):
    """
    Проверяем, что метод отмены ордера использует блокировку строки (for_update=True).
    SQLite (используемый в тестах) не поддерживает реальную блокировку FOR UPDATE, 
    поэтому мы проверяем вызов мока.
    """
    from unittest.mock import AsyncMock, patch
    from app.database.models.order import Order

    svc = OrderService(session, encryption_service)
    
    with patch("app.repositories.order_repo.OrderRepository.get_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Order(
            id=1, 
            user_id=sample_user.id, 
            status=OrderStatusEnum.created, 
            order_type=OrderTypeEnum.sell,
            payment_link_snapshot=None
        )
        
        await svc.cancel_order(order_id=1, user_id=sample_user.id)
        
        # Проверяем что get_by_id был вызван с for_update=True
        mock_get.assert_awaited_once_with(1, for_update=True)
