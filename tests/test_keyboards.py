from pathlib import Path

from keyboards.inline import (
    get_admin_menu_keyboard,
    get_language_menu_keyboard,
    get_main_menu_keyboard,
    get_reports_list_keyboard,
    get_users_list_keyboard,
)


def _flatten(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_main_menu_hides_settings_for_non_admin():
    markup = get_main_menu_keyboard(is_admin=False, lang="en")
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "admin:menu" not in callback_data
    assert "search:new" in callback_data
    assert "reports:list" in callback_data


def test_main_menu_shows_settings_for_admin():
    markup = get_main_menu_keyboard(is_admin=True, lang="en")
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "admin:menu" in callback_data


def test_main_menu_has_language_button():
    markup = get_main_menu_keyboard(is_admin=False, lang="en")
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "lang:menu" in callback_data


def test_main_menu_localizes_button_text():
    markup_en = get_main_menu_keyboard(is_admin=False, lang="en")
    markup_uk = get_main_menu_keyboard(is_admin=False, lang="uk")
    texts_en = [b.text for b in _flatten(markup_en)]
    texts_uk = [b.text for b in _flatten(markup_uk)]
    assert "🔍 New search" in texts_en
    assert "🔍 Новий пошук" in texts_uk


def test_admin_menu_labels_reflect_state():
    markup = get_admin_menu_keyboard(access_mode="whitelist", ghunt_enabled=False, lang="en")
    texts = [b.text for b in _flatten(markup)]
    assert any("Whitelist" in t for t in texts)
    assert any("Disabled" in t for t in texts)

    markup_open = get_admin_menu_keyboard(access_mode="open", ghunt_enabled=True, lang="en")
    texts_open = [b.text for b in _flatten(markup_open)]
    assert any("Open" in t for t in texts_open)
    assert any("Enabled" in t for t in texts_open)


def test_users_list_keyboard_has_delete_button_per_user_and_add_button():
    markup = get_users_list_keyboard([111, 222], lang="en")
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "admin:deluser:111" in callback_data
    assert "admin:deluser:222" in callback_data
    assert "admin:adduser" in callback_data


def test_reports_list_keyboard_one_button_per_report():
    reports = [Path("20260910_120000_mrmozozavr.html"), Path("20260909_090000_user_example_com.html")]
    markup = get_reports_list_keyboard(reports, lang="en")
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "reports:send:0" in callback_data
    assert "reports:send:1" in callback_data
    assert "menu:main" in callback_data


def test_language_menu_has_one_button_per_supported_language():
    markup = get_language_menu_keyboard(current="en")
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "lang:set:en" in callback_data
    assert "lang:set:uk" in callback_data
    assert "lang:set:pl" in callback_data


def test_language_menu_marks_current_language():
    markup = get_language_menu_keyboard(current="uk")
    texts = [b.text for b in _flatten(markup)]
    assert any(t.startswith("✅") and "Українська" in t for t in texts)
