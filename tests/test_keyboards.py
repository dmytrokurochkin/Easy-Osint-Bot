from pathlib import Path

from bot.keyboards import admin_menu, main_menu, reports_list_menu, users_list_menu


def _flatten(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_main_menu_hides_settings_for_non_admin():
    markup = main_menu(is_admin=False)
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "admin:menu" not in callback_data
    assert "search:new" in callback_data
    assert "reports:list" in callback_data


def test_main_menu_shows_settings_for_admin():
    markup = main_menu(is_admin=True)
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "admin:menu" in callback_data


def test_admin_menu_labels_reflect_state():
    markup = admin_menu(access_mode="whitelist", ghunt_enabled=False)
    texts = [b.text for b in _flatten(markup)]
    assert any("Whitelist" in t for t in texts)
    assert any("Вимкнено" in t for t in texts)

    markup_open = admin_menu(access_mode="open", ghunt_enabled=True)
    texts_open = [b.text for b in _flatten(markup_open)]
    assert any("Відкритий" in t for t in texts_open)
    assert any("Увімкнено" in t for t in texts_open)


def test_users_list_menu_has_delete_button_per_user_and_add_button():
    markup = users_list_menu([111, 222])
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "admin:deluser:111" in callback_data
    assert "admin:deluser:222" in callback_data
    assert "admin:adduser" in callback_data


def test_reports_list_menu_one_button_per_report():
    reports = [Path("20260910_120000_mrmozozavr.html"), Path("20260909_090000_user_example_com.html")]
    markup = reports_list_menu(reports)
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "reports:send:0" in callback_data
    assert "reports:send:1" in callback_data
    assert "menu:main" in callback_data
