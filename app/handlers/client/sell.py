"""Handler for selling USDT — FSM OrderSellStates."""

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.order import OrderTypeEnum
from app.database.models.user import RoleEnum
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
from app.utils.helpers import check_fsm_attempts, get_settings_flags

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


async def _create_sell_order(message: Message, state: FSMContext, session: AsyncSession, amount: Decimal, user) -> None:
    """Shared logic to create a sell order after amount and phone are collected."""
    rate_service = RateService(session)
    current_rate = await rate_service.get_current_rate(OrderTypeEnum.sell)
    if current_rate is None:
        await message.answer("Курс продажи не установлен. Обратитесь позже.")
        flags = await get_settings_flags(session)
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

    user_service = UserService(session)
    user = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    if not user.username and not user.phone:
        await state.update_data(amount=str(amount))
        await state.set_state(OrderSellStates.waiting_phone)
        phone_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(
            "Для оформления заявки поделитесь номером телефона:",
            reply_markup=phone_kb,
        )
        return

    await _create_sell_order(message, state, session, amount, user)


@router.message(OrderSellStates.waiting_phone, F.contact)
async def process_sell_phone(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process phone contact for sell order."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка: пользователь не найден. Начните заново (/start).")
        await state.clear()
        return

    if message.contact.phone_number:
        await user_service.set_phone(user.id, message.contact.phone_number)
        user.phone = message.contact.phone_number

    data = await state.get_data()
    amount = Decimal(data["amount"])
    await _create_sell_order(message, state, session, amount, user)


@router.message(OrderSellStates.waiting_phone)
async def invalid_sell_phone(message: Message, state: FSMContext) -> None:
    """Handle invalid input during phone request."""
    should_continue, _ = await check_fsm_attempts(
        state,
        message,
        "Пожалуйста, поделитесь номером телефона через кнопку ниже.",
    )
    if not should_continue:
        return


@router.message(OrderSellStates.waiting_amount)
async def invalid_sell_amount(message: Message, state: FSMContext) -> None:
    """Handle invalid amount input with attempt limit."""
    should_continue, _ = await check_fsm_attempts(
        state,
        message,
        "Введите корректную сумму (положительное число, до 100000 USDT).",
    )
    if not should_continue:
        return
