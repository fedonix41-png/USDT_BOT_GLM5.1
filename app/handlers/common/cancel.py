"""Global cancel handler — clears any active FSM and restores main menu.

Catches the '❌ Отмена' reply button across all FSM states.
Must be registered BEFORE specific FSM handlers so it takes priority.
"""

import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import RoleEnum, User
from app.keyboards.cancel_kb import get_main_keyboard
from app.utils.helpers import get_settings_flags

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "❌ Отмена")
async def cancel_any_fsm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None,
) -> None:
    """Cancel any active FSM flow and restore the main menu."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    logger.info(f"FSM cancelled by user {message.from_user.id}, was in state {current_state}")

    role = user.role if user else RoleEnum.client
    flags = await get_settings_flags(session)
    kb = get_main_keyboard(
        role=role,
        buy_enabled=flags["buy_enabled"],
        sell_enabled=flags["sell_enabled"],
        bot_enabled=flags["bot_enabled"],
        is_super_admin=role == RoleEnum.super_admin,
    )
    await message.answer("❌ Действие отменено.", reply_markup=kb)
