"""Shared helper utilities for handlers."""


from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings

MAX_FSM_ATTEMPTS = 3


async def get_settings_flags(session: AsyncSession) -> dict:
    """Get bot settings flags directly from DB.

    Returns dict with keys 'bot_enabled', 'buy_enabled', 'sell_enabled'.
    Defaults to True if key is absent.
    """
    flags: dict[str, bool] = {"bot_enabled": True, "buy_enabled": True, "sell_enabled": True}
    for key in flags:
        result = await session.get(GlobalSettings, key)
        if result is not None:
            flags[key] = result.value == "1"
    return flags


async def check_fsm_attempts(
    state: FSMContext,
    message: Message,
    error_msg: str = "Введите корректное значение.",
) -> tuple[bool, int]:
    """Check FSM input attempts and increment counter.
    
    Returns:
        Tuple of (should_continue: bool, attempt_count: int)
        If should_continue is False, state is cleared and user is notified.
    """
    data = await state.get_data()
    attempts = data.get("_attempts", 0) + 1

    if attempts >= MAX_FSM_ATTEMPTS:
        await message.answer("Слишком много ошибок. Операция отменена.")
        await state.clear()
        return False, attempts

    await state.update_data(_attempts=attempts)
    await message.answer(error_msg)
    return True, attempts


async def reset_fsm_attempts(state: FSMContext) -> None:
    """Reset FSM attempts counter."""
    data = await state.get_data()
    if "_attempts" in data:
        del data["_attempts"]
        await state.set_data(data)
