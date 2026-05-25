"""FSM states for statistics period selection."""

from aiogram.fsm.state import State, StatesGroup


class StatisticsStates(StatesGroup):
    waiting_start_date = State()
    waiting_end_date = State()
