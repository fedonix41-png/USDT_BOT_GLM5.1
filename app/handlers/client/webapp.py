"""Handler for WebApp data."""

import json
import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.fsm.order_states import OrderBuyStates, OrderSellStates
from app.handlers.client.buy import _create_buy_order
from app.handlers.client.sell import _create_sell_order
from app.services.encryption import EncryptionService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.helpers import reset_fsm_attempts

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.web_app_data, StateFilter(None))
async def handle_webapp_data(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Handle data sent from WebApp via sendData."""
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        amount = Decimal(str(data.get("amount", 0)))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.error(f"Invalid WebApp data received: {message.web_app_data.data}")
        await message.answer("Ошибка обработки данных из WebApp.")
        return

    if amount <= 0 or amount > 100000:
        await message.answer("Некорректная сумма. Попробуйте снова.")
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)

    if action == "buy_usdt":
        if not await settings_service.is_buy_enabled():
            await message.answer("Покупка USDT временно приостановлена.")
            return
        target_fsm = OrderBuyStates
        create_order_func = _create_buy_order
    elif action == "sell_usdt":
        if not await settings_service.is_sell_enabled():
            await message.answer("Продажа USDT временно приостановлена.")
            return
        target_fsm = OrderSellStates
        create_order_func = _create_sell_order
    else:
        await message.answer("Неизвестное действие из WebApp.")
        return

    user_service = UserService(session)
    user = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    if not user.username and not user.phone:
        await state.update_data(amount=str(amount))
        await reset_fsm_attempts(state)
        await state.set_state(target_fsm.waiting_phone)
        phone_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
                [KeyboardButton(text="❌ Отмена")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(
            "Для оформления заявки поделитесь номером телефона:",
            reply_markup=phone_kb,
        )
        return

    # If user has phone/username, create order directly
    await create_order_func(message, state, session, amount, user)
