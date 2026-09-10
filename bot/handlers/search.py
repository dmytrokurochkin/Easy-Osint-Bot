import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.db import get_setting
from bot.keyboards import main_menu
from bot.osint.detect import detect_query_type
from bot.osint.orchestrator import run_tools_for_query
from bot.report.render import render_report

logger = logging.getLogger(__name__)

router = Router(name="search")

REPORTS_DIR = Path("reports")

# In-process guard against a user firing a second search while their first
# one is still running. Single-process bot, so a plain in-memory set is
# sufficient; it does not need to survive a restart.
active_requests: set[int] = set()


class SearchStates(StatesGroup):
    waiting_for_query = State()


@router.callback_query(F.data == "search:new")
async def cb_search_new(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id in active_requests:
        await callback.answer("Зачекай, попередній запит ще виконується.", show_alert=True)
        return
    await state.set_state(SearchStates.waiting_for_query)
    await callback.message.edit_text("Надішли номер телефону, email або юзернейм:")
    await callback.answer()


@router.message(SearchStates.waiting_for_query)
async def on_query(
    message: Message, conn, admin_id: int, blackbird_dir: Path, state: FSMContext
) -> None:
    user_id = message.from_user.id
    if user_id in active_requests:
        await message.answer("Зачекай, попередній запит ще виконується.")
        return

    if not message.text:
        await message.answer("Будь ласка, надішли текстове повідомлення.")
        return

    query = message.text.strip()
    query_type = detect_query_type(query)
    if query_type is None:
        await message.answer(
            "Не розпізнав запит. Надішли номер телефону (з +), email або юзернейм."
        )
        return

    active_requests.add(user_id)
    status_message = await message.answer("⏳ Виконується...")
    try:
        try:
            ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
            results = await run_tools_for_query(
                query, query_type, blackbird_dir=blackbird_dir, ghunt_enabled=ghunt_enabled
            )
            report_path = render_report(
                query, query_type, results, reports_dir=REPORTS_DIR / str(user_id)
            )
            await status_message.edit_text("✅ Готово, надсилаю звіт.")
            await message.answer_document(FSInputFile(report_path))
        except Exception:
            logger.exception("Search failed for user_id=%s query=%r", user_id, query)
            await status_message.edit_text("❌ Сталася помилка під час виконання пошуку.")
    finally:
        active_requests.discard(user_id)
        await state.clear()
        is_admin = user_id == admin_id
        await message.answer("Обери дію:", reply_markup=main_menu(is_admin))
