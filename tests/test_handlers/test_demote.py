import pytest
from unittest.mock import AsyncMock, MagicMock

from app.database.models.user import RoleEnum, User
from app.fsm.role_states import DemoteOperatorStates, DemoteAdminStates
from app.handlers.admin.assign_roles import process_demote_operator, process_demote_admin


@pytest.mark.asyncio
async def test_process_demote_operator_success(session):
    # Setup users
    executor = User(
        telegram_id=111,
        username="executor",
        full_name="Executor Admin",
        role=RoleEnum.admin,
    )
    target = User(
        telegram_id=222,
        username="target_op",
        full_name="Target Operator",
        role=RoleEnum.operator,
    )
    session.add(executor)
    session.add(target)
    await session.flush()

    # Mock Message
    message = AsyncMock()
    message.text = "222"
    message.from_user.id = executor.telegram_id
    message.bot = AsyncMock()
    message.bot.send_message = AsyncMock()

    # Mock FSMContext
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})

    # Call handler
    await process_demote_operator(message, state, session, executor)

    # Verify target user was demoted in DB
    await session.refresh(target)
    assert target.role == RoleEnum.client

    # Verify state cleared
    state.clear.assert_called_once()
    message.answer.assert_called()


@pytest.mark.asyncio
async def test_process_demote_operator_not_operator(session):
    # Setup users
    executor = User(
        telegram_id=111,
        username="executor",
        full_name="Executor Admin",
        role=RoleEnum.admin,
    )
    target = User(
        telegram_id=222,
        username="target_client",
        full_name="Target Client",
        role=RoleEnum.client,
    )
    session.add(executor)
    session.add(target)
    await session.flush()

    # Mock Message
    message = AsyncMock()
    message.text = "222"
    message.from_user.id = executor.telegram_id

    # Mock FSMContext
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})

    # Call handler
    await process_demote_operator(message, state, session, executor)

    # Verify target user role did not change
    await session.refresh(target)
    assert target.role == RoleEnum.client

    # State not cleared (attempts logic)
    state.clear.assert_not_called()


@pytest.mark.asyncio
async def test_process_demote_admin_success(session):
    # Setup users
    executor = User(
        telegram_id=100200300,
        username="executor_super",
        full_name="Super Admin",
        role=RoleEnum.super_admin,
    )
    target = User(
        telegram_id=333,
        username="target_admin",
        full_name="Target Admin",
        role=RoleEnum.admin,
    )
    session.add(executor)
    session.add(target)
    await session.flush()

    # Mock Message
    message = AsyncMock()
    message.text = "333"
    message.from_user.id = executor.telegram_id
    message.bot = AsyncMock()
    message.bot.send_message = AsyncMock()

    # Mock FSMContext
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})

    # Call handler
    await process_demote_admin(message, state, session, executor)

    # Verify target user was demoted in DB
    await session.refresh(target)
    assert target.role == RoleEnum.client

    # Verify state cleared
    state.clear.assert_called_once()
    message.answer.assert_called()
