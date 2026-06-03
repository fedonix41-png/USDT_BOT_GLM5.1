"""Statistics router for API."""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.statistics import StatisticsResponse
from app.config import settings
from app.database.models.user import RoleEnum, User
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["statistics"])


def parse_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {value}")


@router.get("/api/v1/statistics", response_model=StatisticsResponse)
async def get_statistics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(require_min_role(RoleEnum.operator)),
    session: AsyncSession = Depends(get_session)
):
    if date_from:
        try:
            dt_from = parse_date(date_from)
        except ValueError:
            raise APIValidationError(f"Invalid date_from format: {date_from}")
    else:
        dt_from = datetime.now(UTC) - timedelta(days=30)
        dt_from = dt_from.replace(tzinfo=None)

    if date_to:
        try:
            dt_to = parse_date(date_to)
        except ValueError:
            raise APIValidationError(f"Invalid date_to format: {date_to}")
    else:
        dt_to = datetime.now(UTC).replace(tzinfo=None)

    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))
    stats = await order_service.get_statistics(dt_from, dt_to)

    return StatisticsResponse(
        total_orders=stats.get("total_orders", 0),
        completed_orders=stats.get("completed_orders", 0),
        cancelled_orders=stats.get("cancelled_orders", 0),
        total_volume_usdt=stats.get("total_volume_usdt", 0),
        total_volume_fiat=stats.get("total_volume_fiat", 0),
        buy_orders=stats.get("buy_orders", 0),
        sell_orders=stats.get("sell_orders", 0),
    )
