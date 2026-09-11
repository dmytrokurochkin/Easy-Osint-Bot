import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import get_setting
from keyboards.inline import get_main_menu_keyboard
from locales import get_text
from osint.detect import detect_query_type
from osint.orchestrator import run_tools_for_query
from report.render import render_report

logger = logging.getLogger(__name__)

search_router = Router(name="search")

REPORTS_DIR = Path("reports")

# In-process guard against a user firing a second search while their first
# one is still running. Single-process bot, so a plain in-memory set is
# sufficient; it does not need to survive a restart.
active_requests: set[int] = set()


class SearchStates(StatesGroup):
    waiting_for_query = State()


@search_router.callback_query(F.data == "search:new")
async def cb_search_new(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    if callback.from_user.id in active_requests:
        await callback.answer(get_text(lang, "search_in_progress"), show_alert=True)
        return
    await state.set_state(SearchStates.waiting_for_query)
    await callback.message.edit_text(get_text(lang, "prompt_query"))
    await callback.answer()


@search_router.message(SearchStates.waiting_for_query)
async def on_query(
    message: Message, conn, admin_id: int, blackbird_dir: Path, state: FSMContext, lang: str
) -> None:
    user_id = message.from_user.id
    if user_id in active_requests:
        await message.answer(get_text(lang, "search_in_progress"))
        return

    if not message.text:
        await message.answer(get_text(lang, "please_send_text"))
        return

    query = message.text.strip()
    query_type = detect_query_type(query)
    if query_type is None:
        await message.answer(get_text(lang, "query_not_recognized"))
        return

    active_requests.add(user_id)
    status_message = await message.answer(get_text(lang, "search_running"))
    try:
        try:
            ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
            results = await run_tools_for_query(
                query, query_type, blackbird_dir=blackbird_dir, ghunt_enabled=ghunt_enabled
            )
            report_path = render_report(
                query, query_type, results, reports_dir=REPORTS_DIR / str(user_id), lang=lang
            )
            await status_message.edit_text(get_text(lang, "search_done"))
            await message.answer_document(FSInputFile(report_path))
        except Exception:
            logger.exception("Search failed for user_id=%s query=%r", user_id, query)
            await status_message.edit_text(get_text(lang, "search_error"))
    finally:
        active_requests.discard(user_id)
        await state.clear()
        is_admin = user_id == admin_id
        await message.answer(
            get_text(lang, "choose_action"), reply_markup=get_main_menu_keyboard(is_admin, lang)
        )
