import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    added_by INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "access_mode": "whitelist",
    "ghunt_enabled": "false",
}


async def init_db(path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(path)
    await conn.executescript(SCHEMA)
    for key, value in DEFAULT_SETTINGS.items():
        await conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    await conn.commit()
    return conn


async def add_user(conn: aiosqlite.Connection, telegram_id: int, added_by: int) -> None:
    await conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, added_by) VALUES (?, ?)",
        (telegram_id, added_by),
    )
    await conn.commit()


async def remove_user(conn: aiosqlite.Connection, telegram_id: int) -> None:
    await conn.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    await conn.commit()


async def list_users(conn: aiosqlite.Connection) -> list[int]:
    cursor = await conn.execute("SELECT telegram_id FROM users ORDER BY added_at")
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def get_setting(conn: aiosqlite.Connection, key: str) -> str:
    cursor = await conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    if row is None:
        raise KeyError(f"Unknown setting: {key}")
    return row[0]


async def set_setting(conn: aiosqlite.Connection, key: str, value: str) -> None:
    await conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await conn.commit()


async def is_authorized(conn: aiosqlite.Connection, telegram_id: int, admin_id: int) -> bool:
    if telegram_id == admin_id:
        return True
    mode = await get_setting(conn, "access_mode")
    if mode == "open":
        return True
    return telegram_id in await list_users(conn)
