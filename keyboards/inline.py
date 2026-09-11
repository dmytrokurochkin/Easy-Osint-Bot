from pathlib import Path

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales import SUPPORTED_LANGUAGES, get_text


def get_main_menu_keyboard(is_admin: bool, lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=get_text(lang, "btn_new_search"), callback_data="search:new")],
        [InlineKeyboardButton(text=get_text(lang, "btn_my_reports"), callback_data="reports:list")],
        [InlineKeyboardButton(text=f"🌐 {SUPPORTED_LANGUAGES[lang]}", callback_data="lang:menu")],
    ]
    if is_admin:
        rows.append(
            [InlineKeyboardButton(text=get_text(lang, "btn_settings"), callback_data="admin:menu")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_menu_keyboard(access_mode: str, ghunt_enabled: bool, lang: str) -> InlineKeyboardMarkup:
    mode_key = "admin_mode_open" if access_mode == "open" else "admin_mode_whitelist"
    ghunt_key = "admin_ghunt_on" if ghunt_enabled else "admin_ghunt_off"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_users"), callback_data="admin:users")],
            [InlineKeyboardButton(text=get_text(lang, mode_key), callback_data="admin:toggle_mode")],
            [InlineKeyboardButton(text=get_text(lang, ghunt_key), callback_data="admin:toggle_ghunt")],
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="menu:main")],
        ]
    )


def get_users_list_keyboard(user_ids: list[int], lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"❌ {uid}", callback_data=f"admin:deluser:{uid}")]
        for uid in user_ids
    ]
    rows.append([InlineKeyboardButton(text=get_text(lang, "btn_add"), callback_data="admin:adduser")])
    rows.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_reports_list_keyboard(reports: list[Path], lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=report.name, callback_data=f"reports:send:{i}")]
        for i, report in enumerate(reports)
    ]
    rows.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_language_menu_keyboard(current: str) -> InlineKeyboardMarkup:
    rows = []
    for code, name in SUPPORTED_LANGUAGES.items():
        label = f"✅ {name}" if code == current else name
        rows.append([InlineKeyboardButton(text=label, callback_data=f"lang:set:{code}")])
    rows.append([InlineKeyboardButton(text=get_text(current, "btn_back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
