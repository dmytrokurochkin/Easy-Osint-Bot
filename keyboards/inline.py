from pathlib import Path

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔍 Новий пошук", callback_data="search:new")],
        [InlineKeyboardButton(text="📄 Мої звіти", callback_data="reports:list")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="⚙️ Налаштування", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_menu_keyboard(access_mode: str, ghunt_enabled: bool) -> InlineKeyboardMarkup:
    mode_label = "🔓 Режим: Відкритий" if access_mode == "open" else "🔒 Режим: Whitelist"
    ghunt_label = "GHunt: 🟢 Увімкнено" if ghunt_enabled else "GHunt: 🔴 Вимкнено"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Користувачі", callback_data="admin:users")],
            [InlineKeyboardButton(text=mode_label, callback_data="admin:toggle_mode")],
            [InlineKeyboardButton(text=ghunt_label, callback_data="admin:toggle_ghunt")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def get_users_list_keyboard(user_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"❌ {uid}", callback_data=f"admin:deluser:{uid}")]
        for uid in user_ids
    ]
    rows.append([InlineKeyboardButton(text="➕ Додати", callback_data="admin:adduser")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_reports_list_keyboard(reports: list[Path]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=report.name, callback_data=f"reports:send:{i}")]
        for i, report in enumerate(reports)
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
