"""Handlers for changing buy/sell exchange rates — FSM ChangeBuyRateStates / ChangeSellRateStates.

FSM is now started from the management panel (mgmt:rate_buy / mgmt:rate_sell callbacks).
"""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum, User
from app.fsm.rate_states import ChangeBuyRateStates, ChangeSellRateStates
from app.keyboards.cancel_kb import get_main_keyboard
from app.services.rate_service import RateService
from app.utils.helpers import check_fsm_attempts, get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


@router.message(ChangeBuyRateStates.waiting_new_rate)
async def process_new_buy_rate(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Process new buy rate."""
    try:
        new_rate = Decimal(message.text.strip())
    except InvalidOperation:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Введите корректный курс (положительное число):"
        )
        return

    if new_rate <= 0:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Введите корректный курс (положительное число):"
        )
        return

    if user is None:
        await message.answer("Ошибка.")
        await state.clear()
        return

    rate_service = RateService(session)
    await rate_service.set_rate(RateTypeEnum.buy, new_rate, user.id)

    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"Курс покупки изменён на {new_rate} RUB/USDT", reply_markup=kb)
    await state.clear()
    logger.info(f"Buy rate changed to {new_rate} by user {user.telegram_id}")


@router.message(ChangeSellRateStates.waiting_new_rate)
async def process_new_sell_rate(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Process new sell rate."""
    try:
        new_rate = Decimal(message.text.strip())
    except InvalidOperation:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Введите корректный курс (положительное число):"
        )
        return

    if new_rate <= 0:
        should_continue, _ = await check_fsm_attempts(
            state, message, "Введите корректный курс (положительное число):"
        )
        return

    if user is None:
        await message.answer("Ошибка.")
        await state.clear()
        return

    rate_service = RateService(session)
    await rate_service.set_rate(RateTypeEnum.sell, new_rate, user.id)

    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"Курс продажи изменён на {new_rate} RUB/USDT", reply_markup=kb)
    await state.clear()
    logger.info(f"Sell rate changed to {new_rate} by user {user.telegram_id}")
