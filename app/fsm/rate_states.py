"""FSM states for rate changes."""

from aiogram.fsm.state import State, StatesGroup


class ChangeBuyRateStates(StatesGroup):
    waiting_new_rate = State()


class ChangeSellRateStates(StatesGroup):
    waiting_new_rate = State()
