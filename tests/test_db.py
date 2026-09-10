import pytest
from bot.db import (
    init_db,
    add_user,
    remove_user,
    list_users,
    get_setting,
    set_setting,
    is_authorized,
)


@pytest.fixture
async def conn():
    connection = await init_db(":memory:")
    yield connection
    await connection.close()


async def test_default_settings_present(conn):
    assert await get_setting(conn, "access_mode") == "whitelist"
    assert await get_setting(conn, "ghunt_enabled") == "false"


async def test_set_setting_overrides_value(conn):
    await set_setting(conn, "access_mode", "open")
    assert await get_setting(conn, "access_mode") == "open"


async def test_add_list_remove_user(conn):
    await add_user(conn, telegram_id=555, added_by=999)
    assert await list_users(conn) == [555]

    await remove_user(conn, 555)
    assert await list_users(conn) == []


async def test_admin_always_authorized(conn):
    await set_setting(conn, "access_mode", "whitelist")
    assert await is_authorized(conn, telegram_id=999, admin_id=999) is True


async def test_open_mode_authorizes_anyone(conn):
    await set_setting(conn, "access_mode", "open")
    assert await is_authorized(conn, telegram_id=12345, admin_id=999) is True


async def test_whitelist_mode_blocks_unknown_user(conn):
    await set_setting(conn, "access_mode", "whitelist")
    assert await is_authorized(conn, telegram_id=12345, admin_id=999) is False


async def test_whitelist_mode_allows_added_user(conn):
    await set_setting(conn, "access_mode", "whitelist")
    await add_user(conn, telegram_id=12345, added_by=999)
    assert await is_authorized(conn, telegram_id=12345, admin_id=999) is True
