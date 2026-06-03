"""Orders router for API."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_min_role
from app.api.exceptions import NotFoundError, ValidationError as APIValidationError
from app.api.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)
from app.config import settings
from app.database.models.order import OrderStatusEnum, OrderTypeEnum
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum, User
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService

async def notify_order_status_bg(
    order_id: int, operator_id: int, status: str, rejection_reason: str | None = None
) -> None:
    """Sends background Telegram notifications for order status updates."""
    try:
        from aiogram import Bot

        from app.database.models.order import OrderStatusEnum
        from app.repositories.user_repo import UserRepository
        from app.services.encryption import EncryptionService
        from app.services.notification_service import NotificationService
        from app.services.order_service import OrderService
        from app.database.engine import async_session_maker

        async with async_session_maker() as session:
            order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))
            user_repo = UserRepository(session)

            order = await order_service.get_order_by_id(order_id)
            operator = await user_repo.get_by_id(operator_id)

            if not order or not operator:
                logger.error(
                    f"Bg notification failed: order {order_id} or operator {operator_id} not found"
                )
                return

            client_user = await user_repo.get_by_id(order.user_id)
            recipient_chat_id = order.chat_id or (client_user.telegram_id if client_user else None)

            async with Bot(token=settings.BOT_TOKEN) as bot:
                if status == OrderStatusEnum.completed.value:
                    if recipient_chat_id:
                        order_type_str = "покупку" if order.order_type.value == "buy" else "продажу"
                        client_text = (
                            f"✅ Ваша заявка #{order_id} на {order_type_str} {order.amount_usdt} USDT подтверждена!\n"
                            f"К оплате: {order.total_fiat} RUB\n"
                            f"Оператор: @{operator.username or 'N/A'}\n"
                            f"Спасибо за обращение!"
                        )
                        try:
                            await bot.send_message(chat_id=recipient_chat_id, text=client_text)
                        except Exception as e:
                            logger.error(f"Failed to send direct message to client in bg: {e}")

                    try:
                        notif_service = NotificationService(session)
                        await notif_service.notify_order_completed(bot, order, operator)
                    except Exception as e:
                        logger.error(f"Failed to send operators alerts in bg: {e}")

                elif status == OrderStatusEnum.cancelled.value:
                    if recipient_chat_id:
                        reason_str = (
                            f"\nПричина: {rejection_reason}" if rejection_reason else ""
                        )
                        client_text = (
                            f"❌ Ваша заявка #{order_id} на "
                            f"{'покупку' if order.order_type.value == 'buy' else 'продажу'} "
                            f"{order.amount_usdt} USDT отменена администратором.{reason_str}"
                        )
                        try:
                            await bot.send_message(chat_id=recipient_chat_id, text=client_text)
                        except Exception as e:
                            logger.error(f"Failed to send cancellation message to client in bg: {e}")
    except Exception as e:
        logger.error(f"Unhandled exception in background notification: {e}")


logger = logging.getLogger(__name__)
router = APIRouter(tags=["orders"])


def parse_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime format: {value}")


@router.post("/api/v1/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: OrderCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if order_data.amount_usdt < Decimal("10.0"):
        raise APIValidationError("Minimum amount is 10 USDT")

    settings_service = SettingsService(session, EncryptionService(settings.ENCRYPTION_KEY))
    rate_service = RateService(session)
    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))

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

    is_paid_from_balance = False
    if order_data.order_type == OrderTypeEnum.sell:
        if current_user.balance >= order_data.amount_usdt:
            current_user.balance = current_user.balance - order_data.amount_usdt
            is_paid_from_balance = True
            await session.flush()

    client_details = order_data.client_details
    if is_paid_from_balance:
        client_details = f"[BALANCE_PAID]{client_details}"

    order = await order_service.create_order_web(
        user_id=current_user.id,
        order_type=order_data.order_type,
        amount_usdt=order_data.amount_usdt,
        rate=rate,
        client_details=client_details,
    )

    await session.commit()

    logger.info(
        f"User {current_user.telegram_id} created {order_data.order_type.value} order "
        f"for {order_data.amount_usdt} USDT"
    )

    # Notify operators in Telegram notification chats
    from aiogram import Bot

    from app.services.notification_service import NotificationService
    try:
        async with Bot(token=settings.BOT_TOKEN) as bot:
            notif_service = NotificationService(session)
            await notif_service.notify_new_order(bot, order, current_user)
    except Exception as e:
        logger.error(f"Failed to send Telegram notification for web order #{order.id}: {e}")

    return OrderResponse.model_validate(order)


@router.get("/api/v1/orders", response_model=OrderListResponse)
async def list_orders(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_min_role(RoleEnum.operator)),
    session: AsyncSession = Depends(get_session),
):
    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))
    orders = await order_service.get_active_orders(offset=offset, limit=limit)
    total = await order_service.count_active_orders()

    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/api/v1/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(require_min_role(RoleEnum.operator)),
    session: AsyncSession = Depends(get_session),
):
    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))
    order = await order_service.get_order_by_id(order_id)

    if order is None:
        raise NotFoundError("Order not found")

    return OrderResponse.model_validate(order)


@router.patch("/api/v1/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    role_levels = {
        RoleEnum.client: 1,
        RoleEnum.operator: 2,
        RoleEnum.admin: 3,
        RoleEnum.super_admin: 4,
    }
    user_level = role_levels.get(current_user.role, 0)

    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))

    if user_level <= role_levels[RoleEnum.client]:
        if status_data.status != OrderStatusEnum.cancelled:
            raise APIValidationError("Clients can only cancel orders")

        order = await order_service.cancel_order_by_client(order_id, current_user.id)

        if order is None:
            raise NotFoundError("Order not found or cannot be cancelled")

        if status_data.rejection_reason:
            order.rejection_reason = status_data.rejection_reason
            await session.flush()

        await session.commit()

        logger.info(f"Client {current_user.telegram_id} cancelled order {order_id}")

        return OrderResponse.model_validate(order)

    # If it reaches here, the user must be at least an operator
    if user_level < role_levels[RoleEnum.operator]:
        raise ForbiddenError(f"Role {current_user.role.value} is not allowed for this action")

    if status_data.status not in (OrderStatusEnum.completed, OrderStatusEnum.cancelled):
        raise APIValidationError("Status must be 'completed' or 'cancelled'")

    if status_data.status == OrderStatusEnum.completed:
        order = await order_service.complete_order(order_id, current_user.id)
    else:
        order = await order_service.reject_order(
            order_id, current_user.id, status_data.rejection_reason
        )

    if order is None:
        raise NotFoundError("Order not found or already processed")

    await session.commit()

    logger.info(f"User {current_user.telegram_id} set status {status_data.status.value} for order {order_id}")

    background_tasks.add_task(
        notify_order_status_bg,
        order_id=order_id,
        operator_id=current_user.id,
        status=status_data.status.value,
        rejection_reason=status_data.rejection_reason,
    )

    return OrderResponse.model_validate(order)


@router.post("/api/v1/orders/{order_id}/complain", response_model=OrderResponse)
async def complain_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))
    order = await order_service.flag_order_broken(order_id, current_user.id)

    if order is None:
        raise NotFoundError("Order not found or not owned by you")

    await session.commit()

    logger.info(f"User {current_user.telegram_id} flagged order {order_id} as broken")

    # Notify operators in Telegram notification chats
    from aiogram import Bot
    from app.services.notification_service import NotificationService

    try:
        async with Bot(token=settings.BOT_TOKEN) as bot:
            notif_service = NotificationService(session)
            await notif_service.notify_broken_link(bot, order, current_user)
    except Exception as e:
        logger.error(f"Failed to send broken link notification for order #{order.id}: {e}")

    return OrderResponse.model_validate(order)
