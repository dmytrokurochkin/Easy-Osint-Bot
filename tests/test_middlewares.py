from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, User

from database import add_user, init_db
from middlewares.auth import AuthMiddleware


@pytest.fixture
async def conn():
    connection = await init_db(":memory:")
    yield connection
    await connection.close()


def _fake_callback(user_id: int) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=user_id, is_bot=False, first_name="X")
    callback.answer = AsyncMock()
    return callback


def _fake_message(user_id: int) -> Message:
    message = MagicMock(spec=Message)
    message.from_user = User(id=user_id, is_bot=False, first_name="X")
    message.answer = AsyncMock()
    return message


async def test_unauthorized_callback_is_blocked_and_handler_not_called(conn):
    handler = AsyncMock()
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_not_called()
    callback.answer.assert_awaited_once_with("Доступ закрито.", show_alert=True)
    assert result is None


async def test_unauthorized_message_is_blocked_and_handler_not_called(conn):
    handler = AsyncMock()
    message = _fake_message(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": message.from_user}

    result = await AuthMiddleware()(handler, message, data)

    handler.assert_not_called()
    message.answer.assert_awaited_once_with(
        "Доступ закрито. Звернись до адміністратора бота."
    )
    assert result is None


async def test_admin_is_always_authorized_and_handler_runs(conn):
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=1)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_awaited_once_with(callback, data)
    callback.answer.assert_not_called()
    assert result == "handled"


async def test_whitelisted_user_is_authorized_and_handler_runs(conn):
    await add_user(conn, telegram_id=42, added_by=1)
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_awaited_once_with(callback, data)
    assert result == "handled"


async def test_removed_user_is_reauthorized_out_on_next_request(conn):
    """Regression test for the core finding: a user who was once
    whitelisted and then removed by the admin must be blocked on their
    very next request (e.g. pressing a button on an old cached message),
    not just on their next /start."""
    from database import remove_user

    await add_user(conn, telegram_id=42, added_by=1)
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    # First request succeeds while whitelisted.
    result = await AuthMiddleware()(handler, callback, data)
    assert result == "handled"

    # Admin removes the user via the admin panel.
    await remove_user(conn, 42)

    # The same (old, cached) button press must now be blocked.
    handler.reset_mock()
    callback.answer.reset_mock()
    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_not_called()
    callback.answer.assert_awaited_once_with("Доступ закрито.", show_alert=True)
    assert result is None
