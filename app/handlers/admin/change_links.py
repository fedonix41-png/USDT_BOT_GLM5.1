"""Handler for changing payment links — FSM ChangeLinksStates."""

import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.global_settings import GlobalSettings
from app.database.models.order import OrderTypeEnum, OrderStatusEnum
from app.database.models.user import RoleEnum, User
from app.fsm.links_states import ChangeLinksStates
from app.keyboards.admin_kb import admin_keyboard
from app.keyboards.inline_kb import link_type_kb
from app.services.encryption import EncryptionService
from app.services.order_service import OrderService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.formatting import format_order_message

logger = logging.getLogger(__name__)

router = Router()


async def _get_settings_flags(session: AsyncSession) -> dict:
    flags = {"bot_enabled": True, "buy_enabled": True, "sell_enabled": True}
    for key in flags:
        result = await session.get(GlobalSettings, key)
        if result is not None:
            flags[key] = result.value == "1"
    return flags


@router.message(F.text == "🔗 Сменить реквизиты", StateFilter(None))
async def start_change_links(message: Message, state: FSMContext) -> None:
    """Initiate change links FSM — choose type."""
    await state.set_state(ChangeLinksStates.choosing_type)
    kb = link_type_kb()
    await message.answer("Выберите тип реквизитов:", reply_markup=kb)


@router.callback_query(ChangeLinksStates.choosing_type, F.data.startswith("link_type:"))
async def choose_link_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle link type selection."""
    link_type = callback.data.split(":")[1]
    order_type = OrderTypeEnum.buy if link_type == "buy" else OrderTypeEnum.sell
    type_str = "покупки" if link_type == "buy" else "продажи"

    await state.update_data(link_type=order_type)
    await state.set_state(ChangeLinksStates.waiting_new_link)
    await callback.message.answer(f"Введите новые реквизиты для {type_str}:")
    await callback.answer()


@router.message(ChangeLinksStates.waiting_new_link)
async def process_new_link(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process new payment link."""
    data = await state.get_data()
    order_type = data["link_type"]
    type_str = "покупки" if order_type == OrderTypeEnum.buy else "продажи"

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Ошибка.")
        await state.clear()
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    await settings_service.set_payment_link(order_type, message.text.strip(), user.id)

    order_service = OrderService(session, encryption)
    broken_orders = await order_service.get_broken_link_orders(order_type)

    if broken_orders:
        for order in broken_orders:
            if order.chat_id and order.message_id:
                try:
                    new_link = await settings_service.get_payment_link(order_type)
                    user_obj = await user_service.get_by_telegram_id(
                        order.user.telegram_id if order.user else 0
                    )
                    text = format_order_message(order, user_obj, new_link)
                    from app.keyboards.inline_kb import order_client_kb
                    kb = order_client_kb(order.id)
                    await message.bot.edit_message_text(
                        chat_id=order.chat_id,
                        message_id=order.message_id,
                        text=text,
                        reply_markup=kb,
                    )
                except Exception as e:
                    logger.error(f"Failed to update message for order #{order.id}: {e}")

            order.link_broken = False
        await session.flush()

    flags = await _get_settings_flags(session)
    kb = admin_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=user.role == RoleEnum.super_admin,
    )
    await message.answer(f"Реквизиты для {type_str} обновлены.", reply_markup=kb)
    await state.clear()
    logger.info(f"Payment link for {type_str} updated by user {user.telegram_id}")
