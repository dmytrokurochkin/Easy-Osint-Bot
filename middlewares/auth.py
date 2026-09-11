import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database import get_user_language, is_authorized
from locales import get_text

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Outer middleware that re-checks whitelist/admin authorization on every
    event, not just on /start, and loads the requesting user's saved
    language preference into `data["lang"]` for every downstream handler.

    Without the auth re-check, a user who was whitelisted once (or used the
    bot while access_mode was "open") keeps a main-menu message in their
    chat with live inline buttons. Telegram lets those buttons be pressed
    forever, regardless of what happens to the user's authorization
    afterwards - so without a re-check here, removing a user via the admin
    panel (or flipping access_mode back to "whitelist") would be purely
    cosmetic.

    Must be registered as an OUTER middleware (not an inner/handler
    middleware) so it runs before FSM state/data is loaded and before the
    wrapped handler executes at all - an unauthorized user must never reach
    handler code.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        conn = data.get("conn")
        admin_id = data.get("admin_id")
        user = data.get("event_from_user")

        if conn is None or admin_id is None or user is None:
            # Nothing to authorize against (should not happen in normal
            # polling setup, since conn/admin_id are passed to
            # start_polling and event_from_user is populated by aiogram's
            # own UserContextMiddleware before router-level middlewares
            # run) - fail open to the handler rather than break unrelated
            # event types.
            return await handler(event, data)

        lang = await get_user_language(conn, user.id)
        data["lang"] = lang

        authorized = await is_authorized(conn, user.id, admin_id)
        if authorized:
            return await handler(event, data)

        logger.info("Blocked unauthorized access attempt by user_id=%s", user.id)

        if isinstance(event, CallbackQuery):
            await event.answer(get_text(lang, "unauthorized_callback"), show_alert=True)
        elif isinstance(event, Message):
            await event.answer(get_text(lang, "unauthorized_message"))
        return None
