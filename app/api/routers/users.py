"""Users router for API."""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_min_role
from app.api.exceptions import ForbiddenError, NotFoundError
from app.api.schemas.order import OrderListResponse, OrderResponse
from app.api.schemas.user import RoleUpdateRequest, UserListResponse, UserResponse, UserUpdateRequest
from app.config import settings
from app.database.models.user import RoleEnum, User
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.user_service import UserService

async def notify_user_block_bg(telegram_id: int, is_blocked: bool) -> None:
    """Sends background Telegram notification when a user is blocked/unblocked."""
    try:
        from aiogram import Bot
        text = "🚫 Вы заблокированы в боте обмена USDT." if is_blocked else "✅ Вы разблокированы в боте обмена USDT."
        async with Bot(token=settings.BOT_TOKEN) as bot:
            await bot.send_message(chat_id=telegram_id, text=text)
    except Exception as e:
        logger.error(f"Failed to send block/unblock alert to telegram in bg: {e}")

async def notify_user_role_bg(telegram_id: int, old_role: str, new_role: str) -> None:
    """Sends background Telegram notification when user role changes."""
    try:
        from aiogram import Bot
        role_names = {
            "super_admin": "Суперадминистратор",
            "admin": "Администратор",
            "operator": "Оператор",
            "client": "Клиент"
        }

        if new_role == "client":
            old_role_name = role_names.get(old_role, "Специальные")
            text = f"👤 С вас сняты полномочия {old_role_name} в боте обмена USDT. Ваша роль изменена на Клиент."
        else:
            new_role_name = role_names.get(new_role, "Специальные")
            text = f"👤 Вы назначены {new_role_name} в боте обмена USDT."

        async with Bot(token=settings.BOT_TOKEN) as bot:
            await bot.send_message(chat_id=telegram_id, text=text)
    except Exception as e:
        logger.error(f"Failed to send role assignment alert to telegram in bg: {e}")

logger = logging.getLogger(__name__)
router = APIRouter(tags=["users"])

@router.get("/api/v1/admin/users", response_model=UserListResponse)
@router.get("/api/v1/users", response_model=UserListResponse)
async def list_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    user_repo = UserRepository(session)
    users = await user_repo.get_all_filtered(search=search, offset=offset, limit=limit)
    total = await user_repo.count_filtered(search=search)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
    )

@router.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise NotFoundError("User not found")

    return UserResponse.model_validate(user)

@router.get("/api/v1/user/profile", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)

@router.get("/api/v1/user/orders", response_model=OrderListResponse)
async def list_current_user_orders(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    order_service = OrderService(session, EncryptionService(settings.ENCRYPTION_KEY))
    orders = await order_service.order_repo.get_user_orders(
        current_user.id, offset=offset, limit=limit
    )
    total = await order_service.order_repo.count_user_orders(current_user.id)

    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        offset=offset,
        limit=limit,
    )

@router.patch("/api/v1/admin/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    update_data: UserUpdateRequest,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    user_repo = UserRepository(session)
    audit_repo = AuditRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise NotFoundError("User not found")

    if update_data.balance is not None:
        user.balance = update_data.balance
    if update_data.fiat_balance is not None:
        user.fiat_balance = update_data.fiat_balance
    if update_data.username is not None:
        user.username = update_data.username
    if update_data.full_name is not None:
        user.full_name = update_data.full_name

    await session.flush()
    await session.commit()

    await audit_repo.log(
        user_id=current_user.id,
        action="update_user",
        details={"target_user_id": user_id, "fields": list(update_data.model_dump(exclude_unset=True).keys())},
    )

    logger.info(f"Admin {current_user.telegram_id} updated user {user.telegram_id}")

    return UserResponse.model_validate(user)

@router.patch("/api/v1/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_data: RoleUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Check permissions based on the role being assigned
    if role_data.role in (RoleEnum.super_admin, RoleEnum.admin):
        # We need super_admin for these. Let's use the min_role dependency manually
        if current_user.role != RoleEnum.super_admin:
            raise ForbiddenError("Only super admin can assign this role")

    user_service = UserService(session)
    user_obj = await user_service.user_repo.get_by_id(user_id)
    if user_obj is None:
        raise NotFoundError("User not found")
        
    old_role = user_obj.role.value

    user = await user_service.set_role(user_id, role_data.role, current_user.id)

    if user is None:
        raise NotFoundError("User not found")

    await session.commit()

    background_tasks.add_task(
        notify_user_role_bg,
        telegram_id=user.telegram_id,
        old_role=old_role,
        new_role=role_data.role.value,
    )

    logger.info(f"User {current_user.telegram_id} set role {role_data.role.value} for user {user.telegram_id}")

    return UserResponse.model_validate(user)

@router.post("/api/v1/users/{user_id}/block", response_model=UserResponse)
async def block_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    user_repo = UserRepository(session)
    audit_repo = AuditRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise NotFoundError("User not found")

    if user.role in (RoleEnum.admin, RoleEnum.super_admin):
        raise ForbiddenError("Cannot block admin users")

    user.is_blocked = True
    await session.flush()
    await session.commit()

    background_tasks.add_task(notify_user_block_bg, user.telegram_id, True)

    await audit_repo.log(
        user_id=current_user.id,
        action="block_user",
        details={"target_user_id": user_id},
    )

    logger.info(f"User {current_user.telegram_id} blocked user {user.telegram_id}")

    return UserResponse.model_validate(user)

@router.delete("/api/v1/users/{user_id}/block", response_model=UserResponse)
async def unblock_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    user_repo = UserRepository(session)
    audit_repo = AuditRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise NotFoundError("User not found")

    user.is_blocked = False
    await session.flush()
    await session.commit()

    background_tasks.add_task(notify_user_block_bg, user.telegram_id, False)

    await audit_repo.log(
        user_id=current_user.id,
        action="unblock_user",
        details={"target_user_id": user_id},
    )

    logger.info(f"User {current_user.telegram_id} unblocked user {user.telegram_id}")

    return UserResponse.model_validate(user)
