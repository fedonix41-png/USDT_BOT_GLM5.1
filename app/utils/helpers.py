"""Shared helper utilities for handlers."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.global_settings import GlobalSettings


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
