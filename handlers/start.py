from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import get_setting
from keyboards.inline import get_admin_menu_keyboard, get_main_menu_keyboard, get_reports_list_keyboard
from locales import get_text

start_router = Router(name="start")


@start_router.message(CommandStart())
async def cmd_start(message: Message, admin_id: int, lang: str) -> None:
    # Authorization itself is enforced by AuthMiddleware (registered as an
    # outer middleware on this router in main.py), which runs before
    # this handler and short-circuits unauthorized requests.
    is_admin = message.from_user.id == admin_id
    await message.answer(get_text(lang, "choose_action"), reply_markup=get_main_menu_keyboard(is_admin, lang))


@start_router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, admin_id: int, lang: str) -> None:
    is_admin = callback.from_user.id == admin_id
    await callback.message.edit_text(
        get_text(lang, "choose_action"), reply_markup=get_main_menu_keyboard(is_admin, lang)
    )
    await callback.answer()


@start_router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, conn, admin_id: int, lang: str) -> None:
    if callback.from_user.id != admin_id:
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    access_mode = await get_setting(conn, "access_mode")
    ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
    await callback.message.edit_text(
        get_text(lang, "settings_title"),
        reply_markup=get_admin_menu_keyboard(access_mode, ghunt_enabled, lang),
    )
    await callback.answer()


REPORTS_DIR = Path("reports")

# Reports persist forever by design (per spec), so a heavy user's history
# can grow without bound. Telegram's InlineKeyboardMarkup has hard limits
# on button/row counts, so the report list must be capped rather than
# building one row per report ever generated.
MAX_REPORTS_SHOWN = 20


def _user_reports(user_id: int) -> list[Path]:
    user_dir = REPORTS_DIR / str(user_id)
    if not user_dir.exists():
        return []
    return sorted(user_dir.glob("*.html"), reverse=True)[:MAX_REPORTS_SHOWN]


@start_router.callback_query(F.data == "reports:list")
async def cb_reports_list(callback: CallbackQuery, lang: str) -> None:
    reports = _user_reports(callback.from_user.id)
    if not reports:
        await callback.answer(get_text(lang, "no_reports_yet"), show_alert=True)
        return
    await callback.message.edit_text(
        get_text(lang, "your_reports"), reply_markup=get_reports_list_keyboard(reports, lang)
    )
    await callback.answer()


@start_router.callback_query(F.data.startswith("reports:send:"))
async def cb_reports_send(callback: CallbackQuery, lang: str) -> None:
    reports = _user_reports(callback.from_user.id)
    index = int(callback.data.removeprefix("reports:send:"))
    if index >= len(reports):
        await callback.answer(get_text(lang, "file_no_longer_exists"), show_alert=True)
        return
    await callback.message.answer_document(FSInputFile(reports[index]))
    await callback.answer()
