"""FSM states for order creation (buy/sell)."""

from aiogram.fsm.state import State, StatesGroup


class OrderBuyStates(StatesGroup):
    waiting_amount = State()
    waiting_phone = State()
    confirm_order = State()


class OrderSellStates(StatesGroup):
    waiting_amount = State()
    waiting_phone = State()
    confirm_order = State()
