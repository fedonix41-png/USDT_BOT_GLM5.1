"""FSM states for role assignment and user management."""

from aiogram.fsm.state import State, StatesGroup


class AssignOperatorStates(StatesGroup):
    waiting_target_user = State()


class AssignAdminStates(StatesGroup):
    waiting_target_user = State()


class BanUserStates(StatesGroup):
    waiting_target_user = State()


class UnbanUserStates(StatesGroup):
    waiting_target_user = State()
