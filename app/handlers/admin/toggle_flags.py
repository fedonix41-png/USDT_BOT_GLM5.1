"""Toggle flags handlers — moved to management.py inline callbacks.

This file kept for backwards compatibility. All toggle logic is now in
the management panel (mgmt:toggle_buy, mgmt:toggle_sell, mgmt:toggle_bot).
"""

import logging

from aiogram import Router

logger = logging.getLogger(__name__)

router = Router()
