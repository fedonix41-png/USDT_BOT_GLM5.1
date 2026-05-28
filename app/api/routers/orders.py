"""Orders router for API."""

import json
import logging
from datetime import datetime

from aiohttp import web
from pydantic import ValidationError

from app.api.deps import get_current_user, require_min_role
from app.api.exceptions import NotFoundError
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.order import OrderListResponse, OrderResponse, OrderStatusUpdateRequest
from app.database.engine import async_session_maker
from app.database.models.order import OrderStatusEnum
from app.database.models.user import RoleEnum
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


def parse_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime format: {value}")


@router.get("/api/v1/orders")
async def list_orders(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.operator)(request)

    offset = int(request.query.get("offset", "0"))
    limit = int(request.query.get("limit", "20"))
    limit = min(limit, 100)

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())
        orders = await order_service.get_active_orders(offset=offset, limit=limit)
        total = await order_service.count_active_orders()

        response = OrderListResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            offset=offset,
            limit=limit,
        )

        return web.json_response(response.model_dump(mode='json'))


@router.get("/api/v1/orders/{order_id}")
async def get_order(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.operator)(request)

    order_id = int(request.match_info["order_id"])

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())
        order = await order_service.get_order_by_id(order_id)

        if order is None:
            raise NotFoundError("Order not found")

        return web.json_response(OrderResponse.model_validate(order).model_dump(mode='json'))


@router.patch("/api/v1/orders/{order_id}/status")
async def update_order_status(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)
    await require_min_role(RoleEnum.operator)(request)

    order_id = int(request.match_info["order_id"])

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        status_data = OrderStatusUpdateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    if status_data.status not in (OrderStatusEnum.completed, OrderStatusEnum.cancelled):
        raise APIValidationError("Status must be 'completed' or 'cancelled'")

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())

        if status_data.status == OrderStatusEnum.completed:
            order = await order_service.complete_order(order_id, current_user.id)
        else:
            order = await order_service.cancel_order(order_id, current_user.id)

        if order is None:
            raise NotFoundError("Order not found or already processed")

        logger.info(f"User {current_user.telegram_id} set status {status_data.status.value} for order {order_id}")

        return web.json_response(OrderResponse.model_validate(order).model_dump(mode='json'))
