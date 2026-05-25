"""Handler for selling USDT — FSM OrderSellStates."""

import logging
from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.order import OrderTypeEnum
from app.database.models.user import RoleEnum, User
from app.fsm.order_states import OrderSellStates
from app.keyboards.cancel_kb import cancel_keyboard, get_main_keyboard
from app.keyboards.client_kb import client_keyboard
from app.keyboards.inline_kb import order_client_kb
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.formatting import format_order_message
from app.utils.helpers import get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "💸 Продать", StateFilter(None))
async def start_sell(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Initiate sell USDT FSM — check if sell is enabled."""
    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)

    if not await settings_service.is_sell_enabled():
        await message.answer("Продажа USDT временно приостановлена.")
        return

    await state.set_state(OrderSellStates.waiting_amount)
    await message.answer(
        "Введите сумму в USDT, которую хотите продать.",
        reply_markup=cancel_keyboard(),
    )


@router.message(OrderSellStates.waiting_amount, F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_sell_amount(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process entered sell amount."""
    try:
        amount = Decimal(message.text.strip())
    except Exception:
        await message.answer("Введите корректную сумму (от 0.01 до 100000 USDT).")
        return

    if amount <= 0 or amount > 100000:
        await message.answer("Введите корректную сумму (от 0.01 до 100000 USDT).")
        return

    rate_service = RateService(session)
    current_rate = await rate_service.get_current_rate(OrderTypeEnum.sell)
    if current_rate is None:
        await message.answer("Курс продажи не установлен. Обратитесь позже.")
        flags = await get_settings_flags(session)
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(message.from_user.id)
        kb = get_main_keyboard(
            role=user.role if user else RoleEnum.client,
            buy_enabled=flags["buy_enabled"],
            sell_enabled=flags["sell_enabled"],
            bot_enabled=flags["bot_enabled"],
            is_super_admin=(user.role == RoleEnum.super_admin if user else False),
        ) if user else client_keyboard()
        await message.answer("Выберите действие:", reply_markup=kb)
        await state.clear()
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    payment_link = await settings_service.get_payment_link(OrderTypeEnum.sell)
    if not payment_link:
        await message.answer("Реквизиты не настроены. Обратитесь позже.")
        flags = await get_settings_flags(session)
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(message.from_user.id)
        kb = get_main_keyboard(
            role=user.role if user else RoleEnum.client,
            buy_enabled=flags["buy_enabled"],
            sell_enabled=flags["sell_enabled"],
            bot_enabled=flags["bot_enabled"],
            is_super_admin=(user.role == RoleEnum.super_admin if user else False),
        ) if user else client_keyboard()
        await message.answer("Выберите действие:", reply_markup=kb)
        await state.clear()
        return

    user_service = UserService(session)
    user = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    order_service = OrderService(session, encryption)
    order = await order_service.create_order(
        user_id=user.id,
        order_type=OrderTypeEnum.sell,
        amount_usdt=amount,
        rate=current_rate,
        payment_link=payment_link,
        message_id=0,
        chat_id=message.chat.id,
    )

    text = format_order_message(order, user, payment_link)
    kb = order_client_kb(order.id)
    sent_message = await message.answer(text, reply_markup=kb)
    await order_service.update_order_message(order.id, sent_message.message_id, message.chat.id)

    from app.services.notification_service import NotificationService
    notif_service = NotificationService(session)
    bot = message.bot
    await notif_service.notify_new_order(bot, order, user)

    # Restore client main menu
    flags = await get_settings_flags(session)
    main_kb = get_main_keyboard(
        role=user.role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer("Выберите действие:", reply_markup=main_kb)

    await state.clear()
    logger.info(f"Sell order #{order.id} created by user {user.telegram_id}, amount={amount}")


@router.message(OrderSellStates.waiting_amount)
async def invalid_sell_amount(message: Message) -> None:
    """Handle invalid amount input."""
    await message.answer("Введите корректную сумму (положительное число, до 100000 USDT).")
