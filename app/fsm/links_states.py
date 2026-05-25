"""FSM states for changing payment links."""

from aiogram.fsm.state import State, StatesGroup


class ChangeLinksStates(StatesGroup):
    choosing_type = State()
    waiting_new_link = State()
