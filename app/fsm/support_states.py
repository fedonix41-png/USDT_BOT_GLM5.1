"""FSM states for support chat."""

from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    waiting_message = State()
