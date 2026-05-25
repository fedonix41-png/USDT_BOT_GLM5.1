"""Handlers for changing buy/sell exchange rates — FSM ChangeBuyRateStates / ChangeSellRateStates."""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings
from app.database.models.order import OrderTypeEnum
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum, User
from app.fsm.rate_states import ChangeBuyRateStates, ChangeSellRateStates
from app.keyboards.admin_kb import admin_keyboard
from app.keyboards.client_kb import client_keyboard
from app.services.rate_service import RateService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


async def _get_settings_flags(session: AsyncSession) -> dict:
    """Get bot settings flags from DB."""
    flags = {"bot_enabled": True, "buy_enabled": True, "sell_enabled": True}
    for key in flags:
        result = await session.get(GlobalSettings, key)
        if result is not None:
            flags[key] = result.value == "1"
    return flags


@router.message(F.text == "🔄 Сменить курс (покупка)", StateFilter(None))
async def start_change_buy_rate(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Initiate change buy rate FSM."""
    rate_service = RateService(session)
    current_rate = await rate_service.get_current_rate(RateTypeEnum.buy)

    current_str = str(current_rate) if current_rate else "Не установлен"
    await state.set_state(ChangeBuyRateStates.waiting_new_rate)
    await message.answer(
        f"Текущий курс покупки: {current_str} RUB/USDT\nВведите новый курс:"
    )


@router.message(ChangeBuyRateStates.waiting_new_rate)
async def process_new_buy_rate(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process new buy rate."""
    try:
        new_rate = Decimal(message.text.strip())
    except InvalidOperation:
        await message.answer("Введите корректный курс (положительное число):")
        return

    if new_rate <= 0:
        await message.answer("Введите корректный курс (положительное число):")
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка.")
        await state.clear()
        return

    rate_service = RateService(session)
    await rate_service.set_rate(RateTypeEnum.buy, new_rate, user.id)

    flags = await _get_settings_flags(session)
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"Курс покупки изменён на {new_rate} RUB/USDT", reply_markup=kb)
    await state.clear()
    logger.info(f"Buy rate changed to {new_rate} by user {user.telegram_id}")


@router.message(F.text == "🔄 Сменить курс (продажа)", StateFilter(None))
async def start_change_sell_rate(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Initiate change sell rate FSM."""
    rate_service = RateService(session)
    current_rate = await rate_service.get_current_rate(RateTypeEnum.sell)

    current_str = str(current_rate) if current_rate else "Не установлен"
    await state.set_state(ChangeSellRateStates.waiting_new_rate)
    await message.answer(
        f"Текущий курс продажи: {current_str} RUB/USDT\nВведите новый курс:"
    )


@router.message(ChangeSellRateStates.waiting_new_rate)
async def process_new_sell_rate(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process new sell rate."""
    try:
        new_rate = Decimal(message.text.strip())
    except InvalidOperation:
        await message.answer("Введите корректный курс (положительное число):")
        return

    if new_rate <= 0:
        await message.answer("Введите корректный курс (положительное число):")
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка.")
        await state.clear()
        return

    rate_service = RateService(session)
    await rate_service.set_rate(RateTypeEnum.sell, new_rate, user.id)

    flags = await _get_settings_flags(session)
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"Курс продажи изменён на {new_rate} RUB/USDT", reply_markup=kb)
    await state.clear()
    logger.info(f"Sell rate changed to {new_rate} by user {user.telegram_id}")
