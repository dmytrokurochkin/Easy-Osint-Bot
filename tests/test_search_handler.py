from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message, User

from database import init_db
from handlers import search


def _fake_message(user_id: int, text: str | None):
    message = MagicMock(spec=Message)
    message.from_user = User(id=user_id, is_bot=False, first_name="X")
    message.text = text

    status_message = MagicMock()
    status_message.edit_text = AsyncMock()
    message.answer = AsyncMock(return_value=status_message)
    message.answer_document = AsyncMock()
    return message, status_message


def _fake_state():
    state = MagicMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


async def test_on_query_with_non_text_message_does_not_crash():
    """Regression test: a sticker/photo/voice note sent while in the
    waiting_for_query FSM state used to crash with
    AttributeError: 'NoneType' object has no attribute 'strip'."""
    conn = await init_db(":memory:")
    try:
        message, _ = _fake_message(user_id=42, text=None)
        state = _fake_state()

        await search.on_query(
            message, conn=conn, admin_id=1, blackbird_dir=Path("."), state=state, lang="en"
        )

        message.answer.assert_awaited_once_with(
            "Please send a text message."
        )
        assert 42 not in search.active_requests
    finally:
        await conn.close()


async def test_on_query_reports_failure_on_status_message_and_still_cleans_up(monkeypatch):
    """Regression test: if run_tools_for_query/render_report/answer_document
    raises, the "in progress" status message must be updated to reflect
    the failure (not left stale) and active_requests/state cleanup must
    still happen."""
    conn = await init_db(":memory:")
    try:

        async def boom(*args, **kwargs):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(search, "run_tools_for_query", boom)

        message, status_message = _fake_message(user_id=42, text="mrmozozavr")
        state = _fake_state()

        await search.on_query(
            message, conn=conn, admin_id=1, blackbird_dir=Path("."), state=state, lang="en"
        )

        status_message.edit_text.assert_awaited_once_with(
            "❌ An error occurred while running the search."
        )
        message.answer_document.assert_not_called()
        assert 42 not in search.active_requests
        state.clear.assert_awaited_once()
        # Cleanup still shows the main menu again after the failure.
        assert message.answer.await_count == 2
    finally:
        await conn.close()
