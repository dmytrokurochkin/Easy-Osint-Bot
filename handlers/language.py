from aiogram import F, Router
from aiogram.types import CallbackQuery

from database import set_user_language
from keyboards.inline import get_language_menu_keyboard, get_main_menu_keyboard
from locales import SUPPORTED_LANGUAGES, get_text

language_router = Router(name="language")


@language_router.callback_query(F.data == "lang:menu")
async def cb_language_menu(callback: CallbackQuery, lang: str) -> None:
    await callback.message.edit_text(
        get_text(lang, "choose_language"), reply_markup=get_language_menu_keyboard(lang)
    )
    await callback.answer()


@language_router.callback_query(F.data.startswith("lang:set:"))
async def cb_set_language(callback: CallbackQuery, conn, admin_id: int) -> None:
    new_lang = callback.data.removeprefix("lang:set:")
    if new_lang not in SUPPORTED_LANGUAGES:
        await callback.answer()
        return
    await set_user_language(conn, callback.from_user.id, new_lang)
    is_admin = callback.from_user.id == admin_id
    await callback.message.edit_text(
        get_text(new_lang, "choose_action"),
        reply_markup=get_main_menu_keyboard(is_admin, new_lang),
    )
    await callback.answer()
