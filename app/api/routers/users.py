"""Users router for API."""

import json
import logging

from aiohttp import web
from pydantic import ValidationError

from app.api.deps import get_current_user, require_min_role
from app.api.exceptions import ForbiddenError, NotFoundError
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.order import OrderListResponse, OrderResponse
from app.api.schemas.user import RoleUpdateRequest, UserListResponse, UserResponse, UserUpdateRequest
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


@router.get("/api/v1/users")
async def list_users(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.admin)(request)

    offset = int(request.query.get("offset", "0"))
    limit = int(request.query.get("limit", "20"))
    limit = min(limit, 100)

    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        users = await user_repo.get_all(offset=offset, limit=limit)
        total = await user_repo.count()

        response = UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            offset=offset,
            limit=limit,
        )

        return web.json_response(response.model_dump(mode='json'))


@router.get("/api/v1/users/{user_id}")
async def get_user(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.admin)(request)

    user_id = int(request.match_info["user_id"])

    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if user is None:
            raise NotFoundError("User not found")

        return web.json_response(UserResponse.model_validate(user).model_dump(mode='json'))


@router.get("/api/v1/user/profile")
async def get_current_user_profile(request: web.Request) -> web.Response:
    """Get current authenticated user profile."""
    current_user = await get_current_user(request)

    return web.json_response(UserResponse.model_validate(current_user).model_dump(mode='json'))


@router.get("/api/v1/user/orders")
async def list_current_user_orders(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)

    offset = int(request.query.get("offset", "0"))
    limit = int(request.query.get("limit", "20"))
    limit = min(limit, 100)

    async with async_session_maker() as session:
        order_service = OrderService(session, EncryptionService())
        orders = await order_service.order_repo.get_user_orders(
            current_user.id, offset=offset, limit=limit
        )
        total = await order_service.order_repo.count_user_orders(current_user.id)

        response = OrderListResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            offset=offset,
            limit=limit,
        )

        return web.json_response(response.model_dump(mode='json'))


@router.patch("/api/v1/admin/users/{user_id}")
async def admin_update_user(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.admin)(request)
    current_user = await get_current_user(request)

    user_id = int(request.match_info["user_id"])

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        update_data = UserUpdateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    async with async_session_maker() as session:
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

        await audit_repo.log(
            user_id=current_user.id,
            action="update_user",
            details={"target_user_id": user_id, "fields": list(data.keys())},
        )

        logger.info(f"Admin {current_user.telegram_id} updated user {user.telegram_id}")

        return web.json_response(UserResponse.model_validate(user).model_dump(mode='json'))


@router.patch("/api/v1/users/{user_id}/role")
async def update_user_role(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)

    user_id = int(request.match_info["user_id"])

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        role_data = RoleUpdateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    if role_data.role == RoleEnum.super_admin:
        await require_min_role(RoleEnum.super_admin)(request)

    if role_data.role == RoleEnum.admin:
        await require_min_role(RoleEnum.super_admin)(request)

    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.set_role(user_id, role_data.role, current_user.id)

        if user is None:
            raise NotFoundError("User not found")

        logger.info(f"User {current_user.telegram_id} set role {role_data.role.value} for user {user.telegram_id}")

        return web.json_response(UserResponse.model_validate(user).model_dump(mode='json'))


@router.post("/api/v1/users/{user_id}/block")
async def block_user(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.admin)(request)
    current_user = await get_current_user(request)

    user_id = int(request.match_info["user_id"])

    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        audit_repo = AuditRepository(session)
        user = await user_repo.get_by_id(user_id)

        if user is None:
            raise NotFoundError("User not found")

        if user.role in (RoleEnum.admin, RoleEnum.super_admin):
            raise ForbiddenError("Cannot block admin users")

        user.is_blocked = True
        await session.flush()

        await audit_repo.log(
            user_id=current_user.id,
            action="block_user",
            details={"target_user_id": user_id},
        )

        logger.info(f"User {current_user.telegram_id} blocked user {user.telegram_id}")

        return web.json_response(UserResponse.model_validate(user).model_dump(mode='json'))


@router.delete("/api/v1/users/{user_id}/block")
async def unblock_user(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.admin)(request)
    current_user = await get_current_user(request)

    user_id = int(request.match_info["user_id"])

    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        audit_repo = AuditRepository(session)
        user = await user_repo.get_by_id(user_id)

        if user is None:
            raise NotFoundError("User not found")

        user.is_blocked = False
        await session.flush()

        await audit_repo.log(
            user_id=current_user.id,
            action="unblock_user",
            details={"target_user_id": user_id},
        )

        logger.info(f"User {current_user.telegram_id} unblocked user {user.telegram_id}")

        return web.json_response(UserResponse.model_validate(user).model_dump(mode='json'))
