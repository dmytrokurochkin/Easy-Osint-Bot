from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import add_user, get_setting, list_users, remove_user, set_setting
from keyboards.inline import get_admin_menu_keyboard, get_users_list_keyboard
from locales import get_text

admin_router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_new_user_id = State()


def _require_admin(user_id: int, admin_id: int) -> bool:
    return user_id == admin_id


@admin_router.callback_query(F.data == "admin:users")
async def cb_users_list(callback: CallbackQuery, conn, admin_id: int, lang: str) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    user_ids = await list_users(conn)
    header = get_text(lang, "users_list_header") if user_ids else get_text(lang, "users_list_empty")
    await callback.message.edit_text(header, reply_markup=get_users_list_keyboard(user_ids, lang))
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin:deluser:"))
async def cb_delete_user(callback: CallbackQuery, conn, admin_id: int, lang: str) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    target_id = int(callback.data.removeprefix("admin:deluser:"))
    await remove_user(conn, target_id)
    user_ids = await list_users(conn)
    header = get_text(lang, "users_list_header") if user_ids else get_text(lang, "users_list_empty")
    await callback.message.edit_text(header, reply_markup=get_users_list_keyboard(user_ids, lang))
    await callback.answer(get_text(lang, "user_deleted"))


@admin_router.callback_query(F.data == "admin:adduser")
async def cb_add_user_prompt(callback: CallbackQuery, admin_id: int, state: FSMContext, lang: str) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_new_user_id)
    await callback.message.edit_text(get_text(lang, "prompt_new_user_id"))
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_new_user_id)
async def on_new_user_id(message: Message, conn, admin_id: int, state: FSMContext, lang: str) -> None:
    if not message.text:
        await message.answer(get_text(lang, "user_id_not_text"))
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer(get_text(lang, "user_id_not_digit"))
        return
    await add_user(conn, telegram_id=int(text), added_by=message.from_user.id)
    await state.clear()
    user_ids = await list_users(conn)
    await message.answer(
        get_text(lang, "user_added_header"), reply_markup=get_users_list_keyboard(user_ids, lang)
    )


@admin_router.callback_query(F.data == "admin:toggle_mode")
async def cb_toggle_mode(callback: CallbackQuery, conn, admin_id: int, lang: str) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    current = await get_setting(conn, "access_mode")
    new_value = "open" if current == "whitelist" else "whitelist"
    await set_setting(conn, "access_mode", new_value)
    ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
    await callback.message.edit_text(
        get_text(lang, "settings_title"),
        reply_markup=get_admin_menu_keyboard(new_value, ghunt_enabled, lang),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin:toggle_ghunt")
async def cb_toggle_ghunt(callback: CallbackQuery, conn, admin_id: int, lang: str) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    current = (await get_setting(conn, "ghunt_enabled")) == "true"
    new_value = "false" if current else "true"
    await set_setting(conn, "ghunt_enabled", new_value)
    access_mode = await get_setting(conn, "access_mode")
    await callback.message.edit_text(
        get_text(lang, "settings_title"),
        reply_markup=get_admin_menu_keyboard(access_mode, new_value == "true", lang),
    )
    await callback.answer()
