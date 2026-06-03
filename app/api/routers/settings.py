"""Settings router for API."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_min_role
from app.api.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.config import settings
from app.database.models.user import RoleEnum, User
from app.services.encryption import EncryptionService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["settings"])


@router.get("/api/v1/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    settings_service = SettingsService(session, EncryptionService(settings.ENCRYPTION_KEY))

    return SettingsResponse(
        bot_enabled=await settings_service.is_bot_enabled(),
        buy_enabled=await settings_service.is_buy_enabled(),
        sell_enabled=await settings_service.is_sell_enabled(),
    )


@router.patch("/api/v1/settings", response_model=SettingsResponse)
async def update_settings(
    settings_data: SettingsUpdateRequest,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    settings_service = SettingsService(session, EncryptionService(settings.ENCRYPTION_KEY))

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

    return SettingsResponse(
        bot_enabled=await settings_service.is_bot_enabled(),
        buy_enabled=await settings_service.is_buy_enabled(),
        sell_enabled=await settings_service.is_sell_enabled(),
    )
