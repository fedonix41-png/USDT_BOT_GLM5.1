"""Settings router for API."""

import json
import logging

from aiohttp import web
from pydantic import ValidationError

from app.api.deps import get_current_user, require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum
from app.services.encryption import EncryptionService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


@router.get("/api/v1/settings")
async def get_settings(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.admin)(request)

    async with async_session_maker() as session:
        settings_service = SettingsService(session, EncryptionService())

        response = SettingsResponse(
            bot_enabled=await settings_service.is_bot_enabled(),
            buy_enabled=await settings_service.is_buy_enabled(),
            sell_enabled=await settings_service.is_sell_enabled(),
        )

        return web.json_response(response.model_dump(mode='json'))


@router.patch("/api/v1/settings")
async def update_settings(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)
    await require_min_role(RoleEnum.admin)(request)

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        settings_data = SettingsUpdateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    async with async_session_maker() as session:
        settings_service = SettingsService(session, EncryptionService())

        updates = []
        if settings_data.bot_enabled is not None:
            await settings_service.toggle_flag("bot_enabled", current_user.id)
            updates.append(f"bot_enabled={settings_data.bot_enabled}")

        if settings_data.buy_enabled is not None:
            await settings_service.toggle_flag("buy_enabled", current_user.id)
            updates.append(f"buy_enabled={settings_data.buy_enabled}")

        if settings_data.sell_enabled is not None:
            await settings_service.toggle_flag("sell_enabled", current_user.id)
            updates.append(f"sell_enabled={settings_data.sell_enabled}")

        logger.info(f"User {current_user.telegram_id} updated settings: {', '.join(updates)}")

        response = SettingsResponse(
            bot_enabled=await settings_service.is_bot_enabled(),
            buy_enabled=await settings_service.is_buy_enabled(),
            sell_enabled=await settings_service.is_sell_enabled(),
        )

        return web.json_response(response.model_dump(mode='json'))
