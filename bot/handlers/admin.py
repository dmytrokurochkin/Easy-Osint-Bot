from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.db import add_user, get_setting, list_users, remove_user, set_setting
from bot.keyboards import admin_menu, users_list_menu

router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_new_user_id = State()


def _require_admin(user_id: int, admin_id: int) -> bool:
    return user_id == admin_id


@router.callback_query(F.data == "admin:users")
async def cb_users_list(callback: CallbackQuery, conn, admin_id: int) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer("Тільки для адміністратора.", show_alert=True)
        return
    user_ids = await list_users(conn)
    await callback.message.edit_text(
        "Користувачі з доступом:" if user_ids else "Список порожній.",
        reply_markup=users_list_menu(user_ids),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:deluser:"))
async def cb_delete_user(callback: CallbackQuery, conn, admin_id: int) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer("Тільки для адміністратора.", show_alert=True)
        return
    target_id = int(callback.data.removeprefix("admin:deluser:"))
    await remove_user(conn, target_id)
    user_ids = await list_users(conn)
    await callback.message.edit_text(
        "Користувачі з доступом:" if user_ids else "Список порожній.",
        reply_markup=users_list_menu(user_ids),
    )
    await callback.answer("Видалено.")


@router.callback_query(F.data == "admin:adduser")
async def cb_add_user_prompt(callback: CallbackQuery, admin_id: int, state: FSMContext) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer("Тільки для адміністратора.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_new_user_id)
    await callback.message.edit_text("Надішли Telegram ID користувача, якого додати:")
    await callback.answer()


@router.message(AdminStates.waiting_for_new_user_id)
async def on_new_user_id(message: Message, conn, admin_id: int, state: FSMContext) -> None:
    if not message.text:
        await message.answer("ID має бути текстовим повідомленням із числом. Спробуй ще раз:")
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("ID має бути числом. Спробуй ще раз:")
        return
    await add_user(conn, telegram_id=int(text), added_by=message.from_user.id)
    await state.clear()
    user_ids = await list_users(conn)
    await message.answer(
        "Користувача додано.\n\nКористувачі з доступом:", reply_markup=users_list_menu(user_ids)
    )


@router.callback_query(F.data == "admin:toggle_mode")
async def cb_toggle_mode(callback: CallbackQuery, conn, admin_id: int) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer("Тільки для адміністратора.", show_alert=True)
        return
    current = await get_setting(conn, "access_mode")
    new_value = "open" if current == "whitelist" else "whitelist"
    await set_setting(conn, "access_mode", new_value)
    ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
    await callback.message.edit_text(
        "Налаштування:", reply_markup=admin_menu(new_value, ghunt_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:toggle_ghunt")
async def cb_toggle_ghunt(callback: CallbackQuery, conn, admin_id: int) -> None:
    if not _require_admin(callback.from_user.id, admin_id):
        await callback.answer("Тільки для адміністратора.", show_alert=True)
        return
    current = (await get_setting(conn, "ghunt_enabled")) == "true"
    new_value = "false" if current else "true"
    await set_setting(conn, "ghunt_enabled", new_value)
    access_mode = await get_setting(conn, "access_mode")
    await callback.message.edit_text(
        "Налаштування:", reply_markup=admin_menu(access_mode, new_value == "true")
    )
    await callback.answer()
