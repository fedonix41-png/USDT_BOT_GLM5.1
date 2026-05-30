"""Orders router for API."""

import json
import logging
from datetime import datetime
from decimal import Decimal

from aiohttp import web
from pydantic import ValidationError

from app.api.deps import get_current_user, require_min_role
from app.api.exceptions import ForbiddenError, NotFoundError
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)
from app.database.engine import async_session_maker
from app.database.models.order import OrderStatusEnum, OrderTypeEnum
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


def parse_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime format: {value}")


@router.post("/api/v1/orders")
async def create_order(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        order_data = OrderCreateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    if order_data.amount_usdt < Decimal("10.0"):
        raise APIValidationError("Minimum amount is 10 USDT")

    async with async_session_maker() as session:
        settings_service = SettingsService(session, EncryptionService())
        rate_service = RateService(session)
        order_service = OrderService(session, EncryptionService())

        if order_data.order_type == OrderTypeEnum.buy:
            buy_enabled = await settings_service.is_buy_enabled()
            if not buy_enabled:
                raise APIValidationError("Buy orders are currently disabled")
            rate = await rate_service.get_current_rate(RateTypeEnum.buy)
        else:
            sell_enabled = await settings_service.is_sell_enabled()
            if not sell_enabled:
                raise APIValidationError("Sell orders are currently disabled")
            rate = await rate_service.get_current_rate(RateTypeEnum.sell)

        if rate is None:
            raise APIValidationError("Rate not set for this order type")

        if order_data.order_type == OrderTypeEnum.sell:
            if current_user.balance < order_data.amount_usdt:
                raise APIValidationError("Insufficient USDT balance")
            current_user.balance = current_user.balance - order_data.amount_usdt
            await session.flush()

        order = await order_service.create_order_web(
            user_id=current_user.id,
            order_type=order_data.order_type,
            amount_usdt=order_data.amount_usdt,
            rate=rate,
            client_details=order_data.client_details,
        )

        logger.info(
            f"User {current_user.telegram_id} created {order_data.order_type.value} order "
            f"for {order_data.amount_usdt} USDT"
        )

        return web.json_response(
            OrderResponse.model_validate(order).model_dump(mode='json'),
            status=201,
        )


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

    role_levels = {
        RoleEnum.client: 1,
        RoleEnum.operator: 2,
        RoleEnum.admin: 3,
        RoleEnum.super_admin: 4,
    }
    user_level = role_levels.get(current_user.role, 0)

    if user_level <= role_levels[RoleEnum.client]:
        if status_data.status != OrderStatusEnum.cancelled:
            raise APIValidationError("Clients can only cancel orders")

        async with async_session_maker() as session:
            order_service = OrderService(session, EncryptionService())
            order = await order_service.cancel_order_by_client(order_id, current_user.id)

            if order is None:
                raise NotFoundError("Order not found or cannot be cancelled")

            if status_data.rejection_reason:
                order.rejection_reason = status_data.rejection_reason
                await session.flush()

            logger.info(f"Client {current_user.telegram_id} cancelled order {order_id}")

            return web.json_response(OrderResponse.model_validate(order).model_dump(mode='json'))

    await require_min_role(RoleEnum.operator)(request)

    if status_data.status not in (OrderStatusEnum.completed, OrderStatusEnum.cancelled):
        raise APIValidationError("Status must be 'completed' or 'cancelled'")

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())

        if status_data.status == OrderStatusEnum.completed:
            order = await order_service.complete_order(order_id, current_user.id)
        else:
            order = await order_service.reject_order(
                order_id, current_user.id, status_data.rejection_reason
            )

        if order is None:
            raise NotFoundError("Order not found or already processed")

        logger.info(f"User {current_user.telegram_id} set status {status_data.status.value} for order {order_id}")

        return web.json_response(OrderResponse.model_validate(order).model_dump(mode='json'))


@router.post("/api/v1/orders/{order_id}/complain")
async def complain_order(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)

    order_id = int(request.match_info["order_id"])

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())
        order = await order_service.flag_order_broken(order_id, current_user.id)

        if order is None:
            raise NotFoundError("Order not found or not owned by you")

        logger.info(f"User {current_user.telegram_id} flagged order {order_id} as broken")

        return web.json_response(OrderResponse.model_validate(order).model_dump(mode='json'))
