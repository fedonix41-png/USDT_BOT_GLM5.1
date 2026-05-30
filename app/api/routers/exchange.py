"""Exchange router for API."""

import json
import logging

from aiohttp import web
from pydantic import ValidationError

from app.api.deps import get_current_user, require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.exchange import ExchangeSettingsResponse, ExchangeSettingsUpdateRequest
from app.database.engine import async_session_maker
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum
from app.repositories.notification_repo import NotificationRepository
from app.services.encryption import EncryptionService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


@router.get("/api/v1/exchange/settings")
async def get_exchange_settings(request: web.Request) -> web.Response:
    await get_current_user(request)

    async with async_session_maker() as session:
        settings_service = SettingsService(session, EncryptionService())
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

        response = ExchangeSettingsResponse(
            buy_rate=buy_rate,
            sell_rate=sell_rate,
            buy_enabled=buy_enabled,
            sell_enabled=sell_enabled,
            bot_enabled=bot_enabled,
            requisites_card=requisites_card,
            requisites_wallet=requisites_wallet,
            notification_chats=notification_chat_ids,
        )

        return web.json_response(response.model_dump(mode='json'))


@router.patch("/api/v1/exchange/settings")
async def update_exchange_settings(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)
    await require_min_role(RoleEnum.admin)(request)

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        settings_data = ExchangeSettingsUpdateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    async with async_session_maker() as session:
        settings_service = SettingsService(session, EncryptionService())
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

        buy_rate = await rate_service.get_current_rate(RateTypeEnum.buy)
        sell_rate = await rate_service.get_current_rate(RateTypeEnum.sell)
        buy_enabled = await settings_service.is_buy_enabled()
        sell_enabled = await settings_service.is_sell_enabled()
        bot_enabled = await settings_service.is_bot_enabled()
        requisites_card = await settings_service.get_requisites_card()
        requisites_wallet = await settings_service.get_requisites_wallet()
        chats = await notification_repo.get_all_chats(active_only=True)
        notification_chat_ids = [str(chat.chat_id) for chat in chats]

        response = ExchangeSettingsResponse(
            buy_rate=buy_rate,
            sell_rate=sell_rate,
            buy_enabled=buy_enabled,
            sell_enabled=sell_enabled,
            bot_enabled=bot_enabled,
            requisites_card=requisites_card,
            requisites_wallet=requisites_wallet,
            notification_chats=notification_chat_ids,
        )

        logger.info(f"User {current_user.telegram_id} updated exchange settings")

        return web.json_response(response.model_dump(mode='json'))
