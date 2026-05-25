"""FSM states for role assignment."""

from aiogram.fsm.state import State, StatesGroup


class AssignOperatorStates(StatesGroup):
    waiting_target_user = State()


class AssignAdminStates(StatesGroup):
    waiting_target_user = State()
