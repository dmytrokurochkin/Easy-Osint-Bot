from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.db import get_setting, is_authorized
from bot.keyboards import admin_menu, main_menu

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, conn, admin_id: int) -> None:
    authorized = await is_authorized(conn, message.from_user.id, admin_id)
    if not authorized:
        await message.answer("Доступ закрито. Звернись до адміністратора бота.")
        return
    is_admin = message.from_user.id == admin_id
    await message.answer("Обери дію:", reply_markup=main_menu(is_admin))


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, admin_id: int) -> None:
    is_admin = callback.from_user.id == admin_id
    await callback.message.edit_text("Обери дію:", reply_markup=main_menu(is_admin))
    await callback.answer()


@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, conn, admin_id: int) -> None:
    if callback.from_user.id != admin_id:
        await callback.answer("Тільки для адміністратора.", show_alert=True)
        return
    access_mode = await get_setting(conn, "access_mode")
    ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
    await callback.message.edit_text(
        "Налаштування:", reply_markup=admin_menu(access_mode, ghunt_enabled)
    )
    await callback.answer()
