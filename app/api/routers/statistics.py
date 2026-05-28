"""Statistics router for API."""

import logging
from datetime import datetime, timedelta

from aiohttp import web

from app.api.deps import require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.statistics import StatisticsResponse
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


def parse_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {value}")


@router.get("/api/v1/statistics")
async def get_statistics(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.operator)(request)

    date_from_str = request.query.get("date_from")
    date_to_str = request.query.get("date_to")

    if date_from_str:
        try:
            date_from = parse_date(date_from_str)
        except ValueError:
            raise APIValidationError(f"Invalid date_from format: {date_from_str}")
    else:
        date_from = datetime.utcnow() - timedelta(days=30)

    if date_to_str:
        try:
            date_to = parse_date(date_to_str)
        except ValueError:
            raise APIValidationError(f"Invalid date_to format: {date_to_str}")
    else:
        date_to = datetime.utcnow()

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())
        stats = await order_service.get_statistics(date_from, date_to)

        response = StatisticsResponse(
            total_orders=stats.get("total_orders", 0),
            completed_orders=stats.get("completed_orders", 0),
            cancelled_orders=stats.get("cancelled_orders", 0),
            total_volume_usdt=stats.get("total_volume_usdt", 0),
            total_volume_fiat=stats.get("total_volume_fiat", 0),
            buy_orders=stats.get("buy_orders", 0),
            sell_orders=stats.get("sell_orders", 0),
        )

        return web.json_response(response.model_dump(mode='json'))
