"""Exchange router for API."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.exchange import ExchangeSettingsResponse, ExchangeSettingsUpdateRequest
from app.config import settings
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum, User
from app.repositories.notification_repo import NotificationRepository
from app.services.encryption import EncryptionService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["exchange"])


@router.get("/api/v1/exchange/settings", response_model=ExchangeSettingsResponse)
async def get_exchange_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    settings_service = SettingsService(session, EncryptionService(settings.ENCRYPTION_KEY))
    rate_service = RateService(session)
    notification_repo = NotificationRepository(session)

    buy_rate = await rate_service.get_current_rate(RateTypeEnum.buy)
    sell_rate = await rate_service.get_current_rate(RateTypeEnum.sell)
    buy_enabled = await settings_service.is_buy_enabled()
    sell_enabled = await settings_service.is_sell_enabled()
    bot_enabled = await settings_service.is_bot_enabled()
    requisites_card = await settings_service.get_requisites_card()
    requisites_wallet = await settings_service.get_requisites_wallet()

    chats = await notification_repo.get_all_chats(active_only=True)
    notification_chat_ids = [str(chat.chat_id) for chat in chats]

    return ExchangeSettingsResponse(
        buy_rate=buy_rate,
        sell_rate=sell_rate,
        buy_enabled=buy_enabled,
        sell_enabled=sell_enabled,
        bot_enabled=bot_enabled,
        requisites_card=requisites_card,
        requisites_wallet=requisites_wallet,
        notification_chats=notification_chat_ids,
    )


@router.patch("/api/v1/exchange/settings", response_model=ExchangeSettingsResponse)
async def update_exchange_settings(
    settings_data: ExchangeSettingsUpdateRequest,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    settings_service = SettingsService(session, EncryptionService(settings.ENCRYPTION_KEY))
    rate_service = RateService(session)
    notification_repo = NotificationRepository(session)

    if settings_data.buy_rate is not None:
        await rate_service.set_rate(RateTypeEnum.buy, settings_data.buy_rate, current_user.id)

    if settings_data.sell_rate is not None:
        await rate_service.set_rate(RateTypeEnum.sell, settings_data.sell_rate, current_user.id)

    if settings_data.bot_enabled is not None:
        current_val = await settings_service.is_bot_enabled()
        if current_val != settings_data.bot_enabled:
            await settings_service.toggle_flag("bot_enabled", current_user.id)

    if settings_data.buy_enabled is not None:
        current_val = await settings_service.is_buy_enabled()
        if current_val != settings_data.buy_enabled:
            await settings_service.toggle_flag("buy_enabled", current_user.id)

    if settings_data.sell_enabled is not None:
        current_val = await settings_service.is_sell_enabled()
        if current_val != settings_data.sell_enabled:
            await settings_service.toggle_flag("sell_enabled", current_user.id)

    if settings_data.requisites_card is not None:
        await settings_service.set_requisites_card(settings_data.requisites_card, current_user.id)

    if settings_data.requisites_wallet is not None:
        await settings_service.set_requisites_wallet(settings_data.requisites_wallet, current_user.id)

    if settings_data.notification_chats is not None:
        existing_chats = await notification_repo.get_all_chats(active_only=False)
        existing_ids = {chat.chat_id for chat in existing_chats}
        new_ids = set()
        for chat_id_str in settings_data.notification_chats:
            try:
                chat_id_int = int(chat_id_str)
                new_ids.add(chat_id_int)
            except ValueError:
                continue

        for chat_id in new_ids - existing_ids:
            await notification_repo.add_chat(chat_id, current_user.id)

        for chat in existing_chats:
            if chat.chat_id not in new_ids:
                await notification_repo.remove_chat(chat.chat_id)

    await session.commit()

    buy_rate = await rate_service.get_current_rate(RateTypeEnum.buy)
    sell_rate = await rate_service.get_current_rate(RateTypeEnum.sell)
    buy_enabled = await settings_service.is_buy_enabled()
    sell_enabled = await settings_service.is_sell_enabled()
    bot_enabled = await settings_service.is_bot_enabled()
    requisites_card = await settings_service.get_requisites_card()
    requisites_wallet = await settings_service.get_requisites_wallet()
    chats = await notification_repo.get_all_chats(active_only=True)
    notification_chat_ids = [str(chat.chat_id) for chat in chats]

    logger.info(f"User {current_user.telegram_id} updated exchange settings")

    return ExchangeSettingsResponse(
        buy_rate=buy_rate,
        sell_rate=sell_rate,
        buy_enabled=buy_enabled,
        sell_enabled=sell_enabled,
        bot_enabled=bot_enabled,
        requisites_card=requisites_card,
        requisites_wallet=requisites_wallet,
        notification_chats=notification_chat_ids,
    )
