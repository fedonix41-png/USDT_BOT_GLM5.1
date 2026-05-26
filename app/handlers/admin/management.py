"""Admin management panel — inline keyboard for toggles and actions.

Reply button ⚙️ Управление opens the inline management panel.
Toggle actions (buy/sell/bot_enabled) update the panel in place.
FSM-triggering actions (rate, links, chats, roles) start state machines.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database.models.user import RoleEnum, User
from app.fsm.links_states import ChangeLinksStates
from app.fsm.rate_states import ChangeBuyRateStates, ChangeSellRateStates
from app.fsm.role_states import AssignAdminStates, AssignOperatorStates
from app.keyboards.cancel_kb import cancel_keyboard
from app.keyboards.management_kb import management_keyboard
from app.services.encryption import EncryptionService
from app.services.rate_service import RateService
from app.services.settings_service import SettingsService
from app.utils.helpers import get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


async def _get_management_kb(session: AsyncSession, is_super_admin: bool) -> management_keyboard:
    """Build management inline keyboard with current flags from DB."""
    flags = await get_settings_flags(session)
    return management_keyboard(
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=is_super_admin,
    )


@router.message(F.text == "⚙️ Управление")
async def show_management_panel(message: Message, session: AsyncSession, user: User | None) -> None:
    """Show inline management panel."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        await message.answer("У вас нет прав для этого действия.")
        return

    kb = await _get_management_kb(session, user.role == RoleEnum.super_admin)
    await message.answer("⚙️ Управление:", reply_markup=kb)


@router.callback_query(F.data == "mgmt:close")
async def close_management_panel(callback: CallbackQuery) -> None:
    """Close the management panel."""
    await callback.message.edit_text("⚙️ Панель закрыта.")
    await callback.answer()


@router.callback_query(F.data == "mgmt:toggle_buy")
async def toggle_buy(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Toggle buy_enabled flag."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    now_enabled = await settings_service.toggle_flag("buy_enabled", user.id)

    text = "✅ Покупка возобновлена." if now_enabled else "🛑 Покупка остановлена."
    kb = await _get_management_kb(session, user.role == RoleEnum.super_admin)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(text, show_alert=False)
    logger.info(f"Buy toggled to {now_enabled} by user {user.telegram_id}")


@router.callback_query(F.data == "mgmt:toggle_sell")
async def toggle_sell(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Toggle sell_enabled flag."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    now_enabled = await settings_service.toggle_flag("sell_enabled", user.id)

    text = "✅ Продажа возобновлена." if now_enabled else "🛑 Продажа остановлена."
    kb = await _get_management_kb(session, user.role == RoleEnum.super_admin)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(text, show_alert=False)
    logger.info(f"Sell toggled to {now_enabled} by user {user.telegram_id}")


@router.callback_query(F.data == "mgmt:toggle_bot")
async def toggle_bot(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    """Toggle bot_enabled flag."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    encryption = EncryptionService(app_settings.ENCRYPTION_KEY)
    settings_service = SettingsService(session, encryption)
    now_enabled = await settings_service.toggle_flag("bot_enabled", user.id)

    if now_enabled:
        text = "✅ Бот включён."
    else:
        text = "🛑 Бот отключён для клиентов."
    kb = await _get_management_kb(session, user.role == RoleEnum.super_admin)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(text, show_alert=False)
    logger.info(f"Bot toggled to {now_enabled} by user {user.telegram_id}")


# --- FSM-triggering callbacks ---

@router.callback_query(F.data == "mgmt:rate_buy")
async def start_change_buy_rate(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User | None) -> None:
    """Start change buy rate FSM from management panel."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    rate_service = RateService(session)
    current_rate = await rate_service.get_current_rate("buy")
    current_str = str(current_rate) if current_rate else "Не установлен"

    await state.set_state(ChangeBuyRateStates.waiting_new_rate)
    await callback.message.edit_text("⚙️ Панель закрыта.")
    await callback.message.answer(
        f"Текущий курс покупки: {current_str} RUB/USDT\nВведите новый курс:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "mgmt:rate_sell")
async def start_change_sell_rate(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User | None) -> None:
    """Start change sell rate FSM from management panel."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    rate_service = RateService(session)
    current_rate = await rate_service.get_current_rate("sell")
    current_str = str(current_rate) if current_rate else "Не установлен"

    await state.set_state(ChangeSellRateStates.waiting_new_rate)
    await callback.message.edit_text("⚙️ Панель закрыта.")
    await callback.message.answer(
        f"Текущий курс продажи: {current_str} RUB/USDT\nВведите новый курс:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "mgmt:links")
async def start_change_links(callback: CallbackQuery, state: FSMContext, user: User | None) -> None:
    """Start change links FSM from management panel."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    from app.keyboards.inline_kb import link_type_kb

    await state.set_state(ChangeLinksStates.choosing_type)
    await callback.message.edit_text("⚙️ Панель закрыта.")
    await callback.message.answer(
        "Выберите тип реквизитов:",
        reply_markup=cancel_keyboard(),
    )
    await callback.message.answer("👇 Покупка / Продажа:", reply_markup=link_type_kb())
    await callback.answer()


@router.callback_query(F.data == "mgmt:chats")
async def start_notification_chats(callback: CallbackQuery, user: User | None) -> None:
    """Show notification chats menu from management panel."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    from app.keyboards.inline_kb import notification_chats_menu_kb

    kb = notification_chats_menu_kb()
    await callback.message.edit_text("⚙️ Управление чатами уведомлений:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "mgmt:assign_operator")
async def start_assign_operator(callback: CallbackQuery, state: FSMContext, user: User | None) -> None:
    """Start assign operator FSM from management panel."""
    if user is None or user.role not in (RoleEnum.admin, RoleEnum.super_admin):
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=admin+")
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    await state.set_state(AssignOperatorStates.waiting_target_user)
    await callback.message.edit_text("⚙️ Панель закрыта.")
    await callback.message.answer(
        "Введите Telegram ID пользователя или перешлите его контакт:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "mgmt:assign_admin")
async def start_assign_admin(callback: CallbackQuery, state: FSMContext, user: User | None) -> None:
    """Start assign admin FSM from management panel (super_admin only)."""
    if user is None or user.role != RoleEnum.super_admin:
        logger.warning(f"Unauthorized access attempt: user_id={callback.from_user.id}, callback={callback.data}, required_role=super_admin")
        await callback.answer("У вас нет прав для этого действия.", show_alert=True)
        return

    await state.set_state(AssignAdminStates.waiting_target_user)
    await callback.message.edit_text("⚙️ Панель закрыта.")
    await callback.message.answer(
        "Введите Telegram ID пользователя или перешлите его контакт:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()
