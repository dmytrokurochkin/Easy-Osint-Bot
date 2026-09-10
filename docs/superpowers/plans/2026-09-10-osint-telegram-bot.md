# OSINT Telegram Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Telegram-бот на aiogram 3.x, керований inline-кнопками, який приймає номер телефону / email / юзернейм, паралельно запускає blackbird+maigret+sherlock (username), holehe(+опційно GHunt) (email), або phonenumbers (phone), і надсилає готовий HTML-звіт документом.

**Architecture:** Один Python asyncio-процес. `bot/osint/runners/*` — тонкі subprocess-обгортки навколо зовнішніх CLI-інструментів (кожна: запуск процесу з timeout → пошук файла результату → парсинг у нормалізований `{"label","value"}` формат). `bot/osint/orchestrator.py` вибирає й паралельно запускає релевантні runner'и по типу запиту. `bot/report/render.py` рендерить Jinja2-шаблон у `.html`-файл. `bot/handlers/*` — aiogram-роутери на callback_data + FSM, `bot/db.py` — aiosqlite для whitelist/settings.

**Tech Stack:** Python 3.11+, aiogram 3.x, aiosqlite, phonenumbers, Jinja2, python-dotenv, pytest + pytest-asyncio. Зовнішні OSINT-інструменти (окремі процеси, не Python-залежності): blackbird (git clone), maigret, holehe, sherlock-project (pip/pipx), GHunt (pipx, опційно).

**Spec:** `docs/superpowers/specs/2026-09-10-osint-telegram-bot-design.md`

## Global Constraints

- Доступ до зовнішньої мережі бот не потребує для власної роботи, крім Telegram API (polling) та subprocess-викликів OSINT-інструментів.
- Жодних API-ключів для базового функціоналу (blackbird, maigret, sherlock, holehe, phonenumbers). GHunt — виняток, потребує ручного `ghunt login` (поза кодом бота).
- Керування ботом — тільки inline-кнопки. Єдина текстова команда: `/start`. Текстовий ввід від користувача приймається лише у двох FSM-станах: сам пошуковий запит, і Telegram ID нового юзера в адмінці.
- Розгортання: polling, без webhook, без Docker як обов'язкової вимоги.
- Кожен subprocess-виклик OSINT-інструмента обмежений таймаутом 120 секунд (`TIMEOUT_SECONDS = 120` в кожному runner-модулі).
- Усі елементи результату будь-якого інструмента нормалізуються до одного формату `{"label": str, "value": str}` перед рендером — так шаблон лишається одним генеричним циклом без розгалужень по типу інструмента.
- UI-текст бота і звіту — українською.
- `settings.access_mode` за замовчуванням `"whitelist"`; `settings.ghunt_enabled` за замовчуванням `"false"`.
- Усі шляхи/прапорці CLI-інструментів у коді нижче звірені з їхнім вихідним кодом (не з README) під час брейнштормінгу цього плану — не змінювати їх "по пам'яті" без перевірки.

---

## File Structure

```
bot/
  __init__.py
  main.py
  config.py
  db.py
  keyboards.py
  osint/
    __init__.py
    types.py
    detect.py
    orchestrator.py
    runners/
      __init__.py
      phone.py
      blackbird.py
      maigret.py
      sherlock.py
      holehe.py
      ghunt.py
  report/
    __init__.py
    render.py
    template.html.j2
  handlers/
    __init__.py
    start.py
    search.py
    admin.py
tests/
  __init__.py
  conftest.py
  test_config.py
  test_db.py
  test_detect.py
  test_phone_runner.py
  test_blackbird_runner.py
  test_maigret_runner.py
  test_sherlock_runner.py
  test_holehe_runner.py
  test_ghunt_runner.py
  test_orchestrator.py
  test_render.py
  test_keyboards.py
  fixtures/
    blackbird_result.json
    maigret_result.json
    sherlock_result.csv
    holehe_result.csv
    ghunt_result.json
reports/
  .gitkeep
data/
  .gitkeep
.env.example
requirements.txt
pytest.ini
.gitignore
README.md
```

---

### Task 1: Project scaffolding + config

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `bot/__init__.py`
- Create: `bot/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `bot.config.Config` (dataclass: `bot_token: str`, `admin_id: int`, `blackbird_dir: Path`), `bot.config.ConfigError(Exception)`, `bot.config.load_config(env: dict | None = None) -> Config`

- [ ] **Step 1: Create `requirements.txt`**

```
aiogram>=3.10,<4
aiosqlite>=0.20
python-dotenv>=1.0
phonenumbers>=8.13
maigret
holehe
sherlock-project
Jinja2>=3.1
pytest>=8.0
pytest-asyncio>=0.24
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Create `.env.example`**

```
BOT_TOKEN=123456789:AAExampleTelegramBotToken
ADMIN_ID=123456789
BLACKBIRD_DIR=C:/path/to/blackbird
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
data/*.sqlite3
reports/*.html
!reports/.gitkeep
!data/.gitkeep
```

- [ ] **Step 5: Create `bot/__init__.py`** (empty file)

- [ ] **Step 6: Write the failing test for config**

`tests/test_config.py`:
```python
import pytest
from pathlib import Path
from bot.config import load_config, ConfigError, Config


def test_load_config_success():
    env = {
        "BOT_TOKEN": "123:ABC",
        "ADMIN_ID": "111222333",
        "BLACKBIRD_DIR": "/opt/blackbird",
    }
    config = load_config(env)
    assert config == Config(
        bot_token="123:ABC",
        admin_id=111222333,
        blackbird_dir=Path("/opt/blackbird"),
    )


def test_load_config_missing_bot_token():
    env = {"ADMIN_ID": "1", "BLACKBIRD_DIR": "/opt/blackbird"}
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(env)


def test_load_config_missing_admin_id():
    env = {"BOT_TOKEN": "123:ABC", "BLACKBIRD_DIR": "/opt/blackbird"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_load_config_admin_id_not_integer():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "not-a-number", "BLACKBIRD_DIR": "/opt/blackbird"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_load_config_missing_blackbird_dir():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "1"}
    with pytest.raises(ConfigError, match="BLACKBIRD_DIR"):
        load_config(env)
```

- [ ] **Step 7: Run tests, verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.config'`

- [ ] **Step 8: Implement `bot/config.py`**

```python
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class Config:
    bot_token: str
    admin_id: int
    blackbird_dir: Path


def load_config(env: dict | None = None) -> Config:
    source = env if env is not None else os.environ

    bot_token = source.get("BOT_TOKEN")
    if not bot_token:
        raise ConfigError("BOT_TOKEN is not set in .env")

    admin_id_raw = source.get("ADMIN_ID")
    if not admin_id_raw:
        raise ConfigError("ADMIN_ID is not set in .env")
    try:
        admin_id = int(admin_id_raw)
    except ValueError:
        raise ConfigError("ADMIN_ID must be an integer Telegram user id") from None

    blackbird_dir_raw = source.get("BLACKBIRD_DIR")
    if not blackbird_dir_raw:
        raise ConfigError("BLACKBIRD_DIR is not set in .env")

    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        blackbird_dir=Path(blackbird_dir_raw),
    )
```

- [ ] **Step 9: Run tests, verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: 5 passed

- [ ] **Step 10: Commit**

```bash
git add requirements.txt pytest.ini .env.example .gitignore bot/__init__.py bot/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: add project scaffolding and .env config loader"
```

---

### Task 2: Database layer (users + settings)

**Files:**
- Create: `bot/db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Consumes: none (standalone)
- Produces: `bot.db.init_db(path: str) -> aiosqlite.Connection`, `bot.db.add_user(conn, telegram_id: int, added_by: int) -> None`, `bot.db.remove_user(conn, telegram_id: int) -> None`, `bot.db.list_users(conn) -> list[int]`, `bot.db.get_setting(conn, key: str) -> str`, `bot.db.set_setting(conn, key: str, value: str) -> None`, `bot.db.is_authorized(conn, telegram_id: int, admin_id: int) -> bool`

- [ ] **Step 1: Write the failing tests**

`tests/test_db.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.db'`

- [ ] **Step 3: Implement `bot/db.py`**

```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bot/db.py tests/test_db.py
git commit -m "feat: add sqlite-backed users/settings storage"
```

---

### Task 3: Query type detection + shared ToolResult type

**Files:**
- Create: `bot/osint/__init__.py`
- Create: `bot/osint/types.py`
- Create: `bot/osint/detect.py`
- Create: `tests/test_detect.py`

**Interfaces:**
- Produces: `bot.osint.types.ToolResult` (dataclass: `tool: str`, `status: str` one of `"ok"|"failed"|"timeout"`, `items: list[dict]` defaulting to `[]`, each item `{"label": str, "value": str}`, `error: str | None = None`), `bot.osint.detect.detect_query_type(text: str) -> str | None` returning `"phone"|"email"|"username"|None`

- [ ] **Step 1: Create `bot/osint/__init__.py`** (empty file)

- [ ] **Step 2: Implement `bot/osint/types.py`**

```python
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    tool: str
    status: str  # "ok" | "failed" | "timeout"
    items: list[dict] = field(default_factory=list)
    error: str | None = None
```

- [ ] **Step 3: Write the failing tests for detection**

`tests/test_detect.py`:
```python
import pytest
from bot.osint.detect import detect_query_type


@pytest.mark.parametrize(
    "text,expected",
    [
        ("+380501234567", "phone"),
        ("+14155552671", "phone"),
        ("test@example.com", "email"),
        ("mrmozozavr", "username"),
        ("mrmozozavr_08.30", "username"),
        ("", None),
        ("   ", None),
        ("not a valid query!!", None),
        ("@", None),
    ],
)
def test_detect_query_type(text, expected):
    assert detect_query_type(text) == expected
```

- [ ] **Step 4: Run tests, verify they fail**

Run: `pytest tests/test_detect.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.detect'`

- [ ] **Step 5: Implement `bot/osint/detect.py`**

```python
import re

import phonenumbers

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,32}$")


def detect_query_type(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None

    if EMAIL_RE.match(text):
        return "email"

    if text.startswith("+"):
        try:
            number = phonenumbers.parse(text, None)
            if phonenumbers.is_valid_number(number):
                return "phone"
        except phonenumbers.NumberParseException:
            pass

    if USERNAME_RE.match(text):
        return "username"

    return None
```

- [ ] **Step 6: Run tests, verify they pass**

Run: `pytest tests/test_detect.py -v`
Expected: 9 passed

- [ ] **Step 7: Commit**

```bash
git add bot/osint/__init__.py bot/osint/types.py bot/osint/detect.py tests/test_detect.py
git commit -m "feat: add query type detection and shared ToolResult type"
```

---

### Task 4: Phone runner (phonenumbers, no subprocess)

**Files:**
- Create: `bot/osint/runners/__init__.py`
- Create: `bot/osint/runners/phone.py`
- Create: `tests/test_phone_runner.py`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`
- Produces: `bot.osint.runners.phone.get_phone_result(query: str) -> ToolResult` (tool `"phone"`)

- [ ] **Step 1: Create `bot/osint/runners/__init__.py`** (empty file)

- [ ] **Step 2: Write the failing tests**

`tests/test_phone_runner.py`:
```python
from bot.osint.runners.phone import get_phone_result


def test_valid_ukrainian_mobile_number():
    result = get_phone_result("+380671234567")
    assert result.tool == "phone"
    assert result.status == "ok"
    labels = {item["label"] for item in result.items}
    assert {"Країна", "Регіон", "Оператор", "Тип лінії", "Часові пояси"} <= labels
    country_item = next(i for i in result.items if i["label"] == "Країна")
    assert country_item["value"] == "+380"


def test_invalid_number_returns_failed():
    result = get_phone_result("+10000000")
    assert result.tool == "phone"
    assert result.status == "failed"
    assert result.error


def test_garbage_input_does_not_raise():
    result = get_phone_result("not-a-number-at-all")
    assert result.status == "failed"
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest tests/test_phone_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.runners.phone'`

- [ ] **Step 4: Implement `bot/osint/runners/phone.py`**

```python
import phonenumbers
from phonenumbers import carrier, geocoder, timezone

from bot.osint.types import ToolResult

LINE_TYPE_NAMES = {
    phonenumbers.PhoneNumberType.MOBILE: "mobile",
    phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
    phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
    phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
    phonenumbers.PhoneNumberType.VOIP: "voip",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal_number",
    phonenumbers.PhoneNumberType.PAGER: "pager",
    phonenumbers.PhoneNumberType.UAN: "uan",
    phonenumbers.PhoneNumberType.UNKNOWN: "unknown",
}


def get_phone_result(query: str) -> ToolResult:
    try:
        number = phonenumbers.parse(query, None)
    except phonenumbers.NumberParseException:
        return ToolResult(tool="phone", status="failed", error="Не вдалося розпізнати номер")

    if not phonenumbers.is_valid_number(number):
        return ToolResult(tool="phone", status="failed", error="Номер невалідний")

    region = geocoder.description_for_number(number, "en") or "невідомо"
    carrier_name = carrier.name_for_number(number, "en") or "невідомо"
    line_type = LINE_TYPE_NAMES.get(phonenumbers.number_type(number), "unknown")
    timezones = ", ".join(timezone.time_zones_for_number(number)) or "невідомо"

    items = [
        {"label": "Країна", "value": f"+{number.country_code}"},
        {"label": "Регіон", "value": region},
        {"label": "Оператор", "value": carrier_name},
        {"label": "Тип лінії", "value": line_type},
        {"label": "Часові пояси", "value": timezones},
    ]
    return ToolResult(tool="phone", status="ok", items=items)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest tests/test_phone_runner.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add bot/osint/runners/__init__.py bot/osint/runners/phone.py tests/test_phone_runner.py
git commit -m "feat: add phone number lookup runner using phonenumbers"
```

---

### Task 5: Shared subprocess test fixture

**Files:**
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: `fake_subprocess` pytest fixture — call it with `fake_subprocess(returncode=0, sleep=None)` inside a test to replace `asyncio.create_subprocess_exec` for the duration of that test with a fake process that does no real work.

- [ ] **Step 1: Implement `tests/conftest.py`**

```python
import asyncio

import pytest


class FakeProcess:
    def __init__(self, returncode: int = 0, sleep: float | None = None):
        self.returncode = returncode
        self._sleep = sleep
        self.killed = False

    async def communicate(self):
        if self._sleep is not None:
            await asyncio.sleep(self._sleep)
        return b"", b""

    def kill(self):
        self.killed = True


@pytest.fixture
def fake_subprocess(monkeypatch):
    def _install(returncode: int = 0, sleep: float | None = None):
        async def fake_create_subprocess_exec(*args, **kwargs):
            return FakeProcess(returncode=returncode, sleep=sleep)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    return _install
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared fake-subprocess fixture for runner tests"
```

---

### Task 6: Blackbird runner

**Files:**
- Create: `bot/osint/runners/blackbird.py`
- Create: `tests/test_blackbird_runner.py`
- Create: `tests/fixtures/blackbird_result.json`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`, `tests/conftest.py::fake_subprocess`
- Produces: `bot.osint.runners.blackbird.run_blackbird(username: str, blackbird_dir: Path) -> ToolResult` (tool `"blackbird"`)

- [ ] **Step 1: Create fixture file `tests/fixtures/blackbird_result.json`**

```json
[
  {
    "name": "GitHub (User)",
    "url": "https://api.github.com/users/mrmozozavr",
    "category": "coding",
    "status": "FOUND",
    "metadata": null
  },
  {
    "name": "Telegram",
    "url": "https://t.me/mrmozozavr",
    "category": "social",
    "status": "FOUND",
    "metadata": null
  }
]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_blackbird_runner.py`:
```python
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from bot.osint.runners import blackbird

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _date_raw() -> str:
    return datetime.now().strftime("%m_%d_%Y")


async def test_run_blackbird_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    result_dir = tmp_path / "results" / f"{username}_{_date_raw()}_blackbird"
    result_dir.mkdir(parents=True)
    result_file = result_dir / f"{username}_{_date_raw()}_blackbird.json"
    shutil.copy(FIXTURES_DIR / "blackbird_result.json", result_file)

    result = await blackbird.run_blackbird(username, tmp_path)

    assert result.tool == "blackbird"
    assert result.status == "ok"
    assert {"label": "GitHub (User)", "value": "https://api.github.com/users/mrmozozavr"} in result.items
    assert len(result.items) == 2


async def test_run_blackbird_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    result = await blackbird.run_blackbird("nobody", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_blackbird_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(blackbird, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await blackbird.run_blackbird("mrmozozavr", tmp_path)
    assert result.status == "timeout"
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest tests/test_blackbird_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.runners.blackbird'`

- [ ] **Step 4: Implement `bot/osint/runners/blackbird.py`**

```python
import asyncio
import json
from datetime import datetime
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [{"label": entry["name"], "value": entry["url"]} for entry in data]


async def run_blackbird(username: str, blackbird_dir: Path) -> ToolResult:
    date_raw = datetime.now().strftime("%m_%d_%Y")

    proc = await asyncio.create_subprocess_exec(
        "python",
        "blackbird.py",
        "--username",
        username,
        "--json",
        cwd=str(blackbird_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="blackbird", status="timeout", error="Перевищено час очікування")

    result_path = (
        Path(blackbird_dir)
        / "results"
        / f"{username}_{date_raw}_blackbird"
        / f"{username}_{date_raw}_blackbird.json"
    )
    if not result_path.exists():
        return ToolResult(tool="blackbird", status="failed", error="Файл результатів не знайдено")

    items = _parse_result_file(result_path)
    return ToolResult(tool="blackbird", status="ok", items=items)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest tests/test_blackbird_runner.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add bot/osint/runners/blackbird.py tests/test_blackbird_runner.py tests/fixtures/blackbird_result.json
git commit -m "feat: add blackbird username runner"
```

---

### Task 7: Maigret runner

**Files:**
- Create: `bot/osint/runners/maigret.py`
- Create: `tests/test_maigret_runner.py`
- Create: `tests/fixtures/maigret_result.json`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`, `tests/conftest.py::fake_subprocess`
- Produces: `bot.osint.runners.maigret.run_maigret(username: str, work_dir: Path) -> ToolResult` (tool `"maigret"`)

- [ ] **Step 1: Create fixture file `tests/fixtures/maigret_result.json`**

```json
{
  "GitHub": {
    "url_user": "https://github.com/mrmozozavr",
    "status": {"status": "Claimed"}
  },
  "Steam": {
    "url_user": "https://steamcommunity.com/id/mrmozozavr",
    "status": {"status": "Claimed"}
  }
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_maigret_runner.py`:
```python
import shutil
from pathlib import Path

from bot.osint.runners import maigret

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_maigret_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    shutil.copy(
        FIXTURES_DIR / "maigret_result.json",
        tmp_path / f"report_{username}_simple.json",
    )

    result = await maigret.run_maigret(username, tmp_path)

    assert result.tool == "maigret"
    assert result.status == "ok"
    assert {"label": "GitHub", "value": "https://github.com/mrmozozavr"} in result.items
    assert len(result.items) == 2


async def test_run_maigret_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    result = await maigret.run_maigret("nobody", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_maigret_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(maigret, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await maigret.run_maigret("mrmozozavr", tmp_path)
    assert result.status == "timeout"
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest tests/test_maigret_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.runners.maigret'`

- [ ] **Step 4: Implement `bot/osint/runners/maigret.py`**

```python
import asyncio
import json
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for sitename, entry in data.items():
        url = entry.get("url_user")
        if url:
            items.append({"label": sitename, "value": url})
    return items


async def run_maigret(username: str, work_dir: Path) -> ToolResult:
    proc = await asyncio.create_subprocess_exec(
        "maigret",
        username,
        "-J",
        "simple",
        "-fo",
        str(work_dir),
        "--no-progressbar",
        "--no-color",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="maigret", status="timeout", error="Перевищено час очікування")

    result_path = Path(work_dir) / f"report_{username}_simple.json"
    if not result_path.exists():
        return ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено")

    items = _parse_result_file(result_path)
    return ToolResult(tool="maigret", status="ok", items=items)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest tests/test_maigret_runner.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add bot/osint/runners/maigret.py tests/test_maigret_runner.py tests/fixtures/maigret_result.json
git commit -m "feat: add maigret username runner"
```

---

### Task 8: Sherlock runner

**Files:**
- Create: `bot/osint/runners/sherlock.py`
- Create: `tests/test_sherlock_runner.py`
- Create: `tests/fixtures/sherlock_result.csv`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`, `tests/conftest.py::fake_subprocess`
- Produces: `bot.osint.runners.sherlock.run_sherlock(username: str, work_dir: Path) -> ToolResult` (tool `"sherlock"`)

- [ ] **Step 1: Create fixture file `tests/fixtures/sherlock_result.csv`**

```csv
username,name,url_main,url_user,exists,http_status,response_time_s
mrmozozavr,GitHub,https://www.github.com/,https://www.github.com/mrmozozavr,Claimed,200,0.4
mrmozozavr,SomeDeadSite,https://dead.example/,https://dead.example/mrmozozavr,Available,404,0.3
```

- [ ] **Step 2: Write the failing tests**

`tests/test_sherlock_runner.py`:
```python
import shutil
from pathlib import Path

from bot.osint.runners import sherlock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_sherlock_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    shutil.copy(FIXTURES_DIR / "sherlock_result.csv", tmp_path / f"{username}.csv")

    result = await sherlock.run_sherlock(username, tmp_path)

    assert result.tool == "sherlock"
    assert result.status == "ok"
    assert {"label": "GitHub", "value": "https://www.github.com/mrmozozavr"} in result.items
    assert len(result.items) == 1  # "Available" row excluded


async def test_run_sherlock_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    result = await sherlock.run_sherlock("nobody", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_sherlock_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(sherlock, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await sherlock.run_sherlock("mrmozozavr", tmp_path)
    assert result.status == "timeout"
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest tests/test_sherlock_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.runners.sherlock'`

- [ ] **Step 4: Implement `bot/osint/runners/sherlock.py`**

```python
import asyncio
import csv
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("exists") != "Claimed":
                continue
            items.append({"label": row.get("name", "unknown"), "value": row.get("url_user", "")})
    return items


async def run_sherlock(username: str, work_dir: Path) -> ToolResult:
    proc = await asyncio.create_subprocess_exec(
        "sherlock",
        username,
        "--csv",
        "--folderoutput",
        str(work_dir),
        "--timeout",
        "60",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="sherlock", status="timeout", error="Перевищено час очікування")

    result_path = Path(work_dir) / f"{username}.csv"
    if not result_path.exists():
        return ToolResult(tool="sherlock", status="failed", error="Файл результатів не знайдено")

    items = _parse_result_file(result_path)
    return ToolResult(tool="sherlock", status="ok", items=items)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest tests/test_sherlock_runner.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add bot/osint/runners/sherlock.py tests/test_sherlock_runner.py tests/fixtures/sherlock_result.csv
git commit -m "feat: add sherlock username runner"
```

---

### Task 9: Holehe runner

**Files:**
- Create: `bot/osint/runners/holehe.py`
- Create: `tests/test_holehe_runner.py`
- Create: `tests/fixtures/holehe_result.csv`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`, `tests/conftest.py::fake_subprocess`
- Produces: `bot.osint.runners.holehe.run_holehe(email: str, work_dir: Path) -> ToolResult` (tool `"holehe"`)

- [ ] **Step 1: Create fixture file `tests/fixtures/holehe_result.csv`**

```csv
name,domain,method,frequent_rate_limit,rateLimit,exists,emailrecovery,phoneNumber,others
github,github.com,register,False,False,True,,,
snapchat,snapchat.com,login,False,False,False,,,
discord,discord.com,register,False,False,True,t***@gmail.com,,
```

- [ ] **Step 2: Write the failing tests**

`tests/test_holehe_runner.py`:
```python
import shutil
from pathlib import Path

from bot.osint.runners import holehe

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_holehe_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)  # holehe always exits 1 on success, see spec
    email = "mrmozozavr@example.com"
    shutil.copy(
        FIXTURES_DIR / "holehe_result.csv",
        tmp_path / f"holehe_1234567890_{email}_results.csv",
    )

    result = await holehe.run_holehe(email, tmp_path)

    assert result.tool == "holehe"
    assert result.status == "ok"
    assert len(result.items) == 2  # only exists == True rows
    github_item = next(i for i in result.items if i["label"] == "github")
    assert github_item["value"] == "знайдено"
    discord_item = next(i for i in result.items if i["label"] == "discord")
    assert "t***@gmail.com" in discord_item["value"]


async def test_run_holehe_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)
    result = await holehe.run_holehe("nobody@example.com", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_holehe_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(holehe, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await holehe.run_holehe("mrmozozavr@example.com", tmp_path)
    assert result.status == "timeout"
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest tests/test_holehe_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.runners.holehe'`

- [ ] **Step 4: Implement `bot/osint/runners/holehe.py`**

```python
import asyncio
import csv
import glob
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("exists") != "True":
                continue
            extras = []
            if row.get("emailrecovery"):
                extras.append(f"відновлення: {row['emailrecovery']}")
            if row.get("phoneNumber"):
                extras.append(f"телефон: {row['phoneNumber']}")
            value = "знайдено" + (" · " + ", ".join(extras) if extras else "")
            items.append({"label": row.get("name", "unknown"), "value": value})
    return items


async def run_holehe(email: str, work_dir: Path) -> ToolResult:
    # holehe writes its CSV to the process's cwd and calls exit() with a
    # string message on success, which always yields returncode=1 — success
    # is therefore judged by the output file's existence, not the exit code.
    proc = await asyncio.create_subprocess_exec(
        "holehe",
        email,
        "--csv",
        "--no-color",
        cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="holehe", status="timeout", error="Перевищено час очікування")

    matches = glob.glob(str(Path(work_dir) / f"holehe_*_{email}_results.csv"))
    if not matches:
        return ToolResult(tool="holehe", status="failed", error="Файл результатів не знайдено")

    items = _parse_result_file(Path(matches[0]))
    return ToolResult(tool="holehe", status="ok", items=items)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest tests/test_holehe_runner.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add bot/osint/runners/holehe.py tests/test_holehe_runner.py tests/fixtures/holehe_result.csv
git commit -m "feat: add holehe email runner"
```

---

### Task 10: GHunt runner (optional, gmail-only)

**Files:**
- Create: `bot/osint/runners/ghunt.py`
- Create: `tests/test_ghunt_runner.py`
- Create: `tests/fixtures/ghunt_result.json`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`, `tests/conftest.py::fake_subprocess`
- Produces: `bot.osint.runners.ghunt.run_ghunt(email: str, work_dir: Path) -> ToolResult` (tool `"ghunt"`)

- [ ] **Step 1: Create fixture file `tests/fixtures/ghunt_result.json`**

```json
{
  "PROFILE_CONTAINER": {
    "profile": {
      "personId": "1234567890",
      "names": {"PROFILE": {"fullname": "Mr Mozozavr"}},
      "profilePhotos": {"PROFILE": {"url": "https://example.com/photo.jpg", "isDefault": false}}
    },
    "play_games": null,
    "maps": {"stats": {"reviews": 3}},
    "calendar": null
  }
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_ghunt_runner.py`:
```python
import shutil
from pathlib import Path

from bot.osint.runners import ghunt

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_ghunt_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)

    async def fake_create(*args, **kwargs):
        # simulate ghunt writing its output file as a side effect of running
        shutil.copy(FIXTURES_DIR / "ghunt_result.json", tmp_path / "ghunt_result.json")
        from tests.conftest import FakeProcess

        return FakeProcess(returncode=0)

    import asyncio

    import pytest

    monkeypatch_target = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = fake_create
    try:
        result = await ghunt.run_ghunt("target@gmail.com", tmp_path)
    finally:
        asyncio.create_subprocess_exec = monkeypatch_target

    assert result.tool == "ghunt"
    assert result.status == "ok"
    assert {"label": "Ім'я профілю", "value": "Mr Mozozavr"} in result.items
    assert {"label": "Gaia ID", "value": "1234567890"} in result.items
    assert any(item["label"] == "Google Maps активність" for item in result.items)


async def test_run_ghunt_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)
    result = await ghunt.run_ghunt("nobody@gmail.com", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_ghunt_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(ghunt, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await ghunt.run_ghunt("target@gmail.com", tmp_path)
    assert result.status == "timeout"
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest tests/test_ghunt_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.runners.ghunt'`

- [ ] **Step 4: Implement `bot/osint/runners/ghunt.py`**

```python
import asyncio
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


def _dig(data: dict, path: list[str]):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _parse_result_file(path: Path) -> list[dict]:
    import json

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profile_container = data.get("PROFILE_CONTAINER")
    if not profile_container:
        return []

    profile = profile_container.get("profile") or {}
    items = []

    full_name = _dig(profile, ["names", "PROFILE", "fullname"])
    if full_name:
        items.append({"label": "Ім'я профілю", "value": full_name})

    gaia_id = profile.get("personId")
    if gaia_id:
        items.append({"label": "Gaia ID", "value": str(gaia_id)})

    photo_url = _dig(profile, ["profilePhotos", "PROFILE", "url"])
    if photo_url:
        items.append({"label": "Фото профілю", "value": photo_url})

    if (profile_container.get("maps") or {}).get("stats"):
        items.append({"label": "Google Maps активність", "value": "знайдено"})

    if profile_container.get("calendar"):
        items.append({"label": "Публічний Google Calendar", "value": "знайдено"})

    return items


async def run_ghunt(email: str, work_dir: Path) -> ToolResult:
    json_path = Path(work_dir) / "ghunt_result.json"

    proc = await asyncio.create_subprocess_exec(
        "ghunt",
        "email",
        email,
        "--json",
        str(json_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="ghunt", status="timeout", error="Перевищено час очікування")

    if not json_path.exists():
        return ToolResult(
            tool="ghunt", status="failed", error="GHunt не авторизований або ціль не знайдена"
        )

    items = _parse_result_file(json_path)
    return ToolResult(tool="ghunt", status="ok", items=items)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest tests/test_ghunt_runner.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add bot/osint/runners/ghunt.py tests/test_ghunt_runner.py tests/fixtures/ghunt_result.json
git commit -m "feat: add optional GHunt gmail runner"
```

---

### Task 11: Orchestrator

**Files:**
- Create: `bot/osint/orchestrator.py`
- Create: `tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`, `bot.osint.runners.phone.get_phone_result`, `bot.osint.runners.blackbird.run_blackbird`, `bot.osint.runners.maigret.run_maigret`, `bot.osint.runners.sherlock.run_sherlock`, `bot.osint.runners.holehe.run_holehe`, `bot.osint.runners.ghunt.run_ghunt`
- Produces: `bot.osint.orchestrator.run_tools_for_query(query: str, query_type: str, blackbird_dir: Path, ghunt_enabled: bool) -> list[ToolResult]`

- [ ] **Step 1: Write the failing tests**

`tests/test_orchestrator.py`:
```python
from pathlib import Path

import pytest

from bot.osint import orchestrator
from bot.osint.types import ToolResult


async def test_phone_query_calls_only_phone_runner(monkeypatch):
    monkeypatch.setattr(
        orchestrator, "get_phone_result", lambda q: ToolResult(tool="phone", status="ok")
    )
    results = await orchestrator.run_tools_for_query(
        "+380671234567", "phone", blackbird_dir=Path("."), ghunt_enabled=False
    )
    assert [r.tool for r in results] == ["phone"]


async def test_username_query_calls_three_runners(monkeypatch, tmp_path):
    async def fake_blackbird(username, blackbird_dir):
        return ToolResult(tool="blackbird", status="ok")

    async def fake_maigret(username, work_dir):
        return ToolResult(tool="maigret", status="ok")

    async def fake_sherlock(username, work_dir):
        return ToolResult(tool="sherlock", status="ok")

    monkeypatch.setattr(orchestrator, "run_blackbird", fake_blackbird)
    monkeypatch.setattr(orchestrator, "run_maigret", fake_maigret)
    monkeypatch.setattr(orchestrator, "run_sherlock", fake_sherlock)

    results = await orchestrator.run_tools_for_query(
        "mrmozozavr", "username", blackbird_dir=Path("."), ghunt_enabled=False
    )
    assert {r.tool for r in results} == {"blackbird", "maigret", "sherlock"}


async def test_email_query_without_ghunt_calls_only_holehe(monkeypatch):
    async def fake_holehe(email, work_dir):
        return ToolResult(tool="holehe", status="ok")

    monkeypatch.setattr(orchestrator, "run_holehe", fake_holehe)

    results = await orchestrator.run_tools_for_query(
        "user@example.com", "email", blackbird_dir=Path("."), ghunt_enabled=False
    )
    assert [r.tool for r in results] == ["holehe"]


async def test_gmail_query_with_ghunt_enabled_calls_both(monkeypatch):
    async def fake_holehe(email, work_dir):
        return ToolResult(tool="holehe", status="ok")

    async def fake_ghunt(email, work_dir):
        return ToolResult(tool="ghunt", status="ok")

    monkeypatch.setattr(orchestrator, "run_holehe", fake_holehe)
    monkeypatch.setattr(orchestrator, "run_ghunt", fake_ghunt)

    results = await orchestrator.run_tools_for_query(
        "user@gmail.com", "email", blackbird_dir=Path("."), ghunt_enabled=True
    )
    assert {r.tool for r in results} == {"holehe", "ghunt"}


async def test_non_gmail_query_with_ghunt_enabled_skips_ghunt(monkeypatch):
    async def fake_holehe(email, work_dir):
        return ToolResult(tool="holehe", status="ok")

    monkeypatch.setattr(orchestrator, "run_holehe", fake_holehe)

    results = await orchestrator.run_tools_for_query(
        "user@yahoo.com", "email", blackbird_dir=Path("."), ghunt_enabled=True
    )
    assert [r.tool for r in results] == ["holehe"]


async def test_unknown_query_type_raises():
    with pytest.raises(ValueError):
        await orchestrator.run_tools_for_query(
            "x", "carrier-pigeon", blackbird_dir=Path("."), ghunt_enabled=False
        )
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.osint.orchestrator'`

- [ ] **Step 3: Implement `bot/osint/orchestrator.py`**

```python
import asyncio
import shutil
import tempfile
from pathlib import Path

from bot.osint.runners.blackbird import run_blackbird
from bot.osint.runners.ghunt import run_ghunt
from bot.osint.runners.holehe import run_holehe
from bot.osint.runners.maigret import run_maigret
from bot.osint.runners.phone import get_phone_result
from bot.osint.runners.sherlock import run_sherlock
from bot.osint.types import ToolResult


async def run_tools_for_query(
    query: str, query_type: str, blackbird_dir: Path, ghunt_enabled: bool
) -> list[ToolResult]:
    if query_type == "phone":
        return [get_phone_result(query)]

    if query_type not in ("username", "email"):
        raise ValueError(f"Unknown query_type: {query_type}")

    work_dir = Path(tempfile.mkdtemp(prefix="osint_"))
    try:
        if query_type == "username":
            results = await asyncio.gather(
                run_blackbird(query, blackbird_dir),
                run_maigret(query, work_dir),
                run_sherlock(query, work_dir),
            )
            return list(results)

        tasks = [run_holehe(query, work_dir)]
        if ghunt_enabled and query.lower().endswith("@gmail.com"):
            tasks.append(run_ghunt(query, work_dir))
        results = await asyncio.gather(*tasks)
        return list(results)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_orchestrator.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add bot/osint/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator dispatching runners by query type"
```

---

### Task 12: Report renderer + HTML template

**Files:**
- Create: `bot/report/__init__.py`
- Create: `bot/report/template.html.j2`
- Create: `bot/report/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `bot.osint.types.ToolResult`
- Produces: `bot.report.render.render_report(query: str, query_type: str, results: list[ToolResult], reports_dir: Path) -> Path`

- [ ] **Step 1: Create `bot/report/__init__.py`** (empty file)

- [ ] **Step 2: Create `bot/report/template.html.j2`**

```html
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OSINT Звіт: {{ query }}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-dark: #0f0d0c;
    --card-bg: rgba(26, 23, 21, 0.75);
    --card-border: rgba(92, 82, 77, 0.4);
    --text-color: #e4deda;
    --text-muted: #8c7e75;
  }
  body { background-color: var(--bg-dark); color: var(--text-color); font-family: 'JetBrains Mono', monospace; }
  .tactical-card { background: var(--card-bg); border: 1px solid var(--card-border); backdrop-filter: blur(8px); }
  .status-ok { color: #9fd8a0; }
  .status-bad { color: #d88a8a; }
  .row { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid rgba(92, 82, 77, 0.15); padding: 8px 0; font-size: 13px; word-break: break-all; }
  .row:last-child { border-bottom: none; }
</style>
</head>
<body class="min-h-screen flex flex-col items-center p-4 sm:p-8">
<main class="max-w-2xl w-full flex flex-col py-8">
  <h1 class="text-3xl font-medium tracking-tight mb-2 text-white">OSINT Звіт: {{ query }}</h1>
  <p class="text-xs text-[#a8998f] mb-8 tracking-widest font-light">
    {{ query_type|upper }} • {{ generated_at }}
  </p>

  {% for result in results %}
  <div class="tactical-card p-5 rounded-none mb-6">
    <div class="flex items-center justify-between mb-4">
      <span class="text-[10px] text-[#a8998f] tracking-wider font-semibold">
        {{ tool_names.get(result.tool, result.tool) }}
      </span>
      {% if result.status == "ok" %}
        <span class="text-[10px] status-ok">&#9679; ОК</span>
      {% else %}
        <span class="text-[10px] status-bad">&#9679; НЕДОСТУПНО</span>
      {% endif %}
    </div>

    {% if result.status == "ok" %}
      {% if result.items %}
        <div class="space-y-1">
          {% for item in result.items %}
          <div class="row">
            <div class="font-bold text-white">{{ item.label }}</div>
            <div class="text-[#8c7e75] text-right">{{ item.value }}</div>
          </div>
          {% endfor %}
        </div>
      {% else %}
        <p class="text-[#8c7e75] text-sm">Нічого не знайдено.</p>
      {% endif %}
    {% else %}
      <p class="text-[#d88a8a] text-sm">{{ result.error or "Інструмент недоступний." }}</p>
    {% endif %}
  </div>
  {% endfor %}

  <footer class="w-full flex flex-col items-center mt-12">
    <p class="text-[9px] text-[#4d443f] tracking-widest pt-2">Згенеровано OSINT-ботом</p>
  </footer>
</main>
</body>
</html>
```

- [ ] **Step 3: Write the failing tests**

`tests/test_render.py`:
```python
from pathlib import Path

from bot.osint.types import ToolResult
from bot.report.render import render_report


def test_render_report_creates_html_file(tmp_path):
    results = [
        ToolResult(
            tool="blackbird",
            status="ok",
            items=[{"label": "GitHub", "value": "https://github.com/mrmozozavr"}],
        ),
        ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено"),
    ]

    out_path = render_report("mrmozozavr", "username", results, reports_dir=tmp_path)

    assert out_path.exists()
    assert out_path.suffix == ".html"
    content = out_path.read_text(encoding="utf-8")
    assert "mrmozozavr" in content
    assert "github.com/mrmozozavr" in content
    assert "НЕДОСТУПНО" in content
    assert "Файл результатів не знайдено" in content


def test_render_report_empty_items_shows_not_found_message(tmp_path):
    results = [ToolResult(tool="holehe", status="ok", items=[])]
    out_path = render_report("user@example.com", "email", results, reports_dir=tmp_path)
    content = out_path.read_text(encoding="utf-8")
    assert "Нічого не знайдено" in content
```

- [ ] **Step 4: Run tests, verify they fail**

Run: `pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.report.render'`

- [ ] **Step 5: Implement `bot/report/render.py`**

```python
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from bot.osint.types import ToolResult

TEMPLATE_DIR = Path(__file__).parent

TOOL_NAMES = {
    "blackbird": "Blackbird",
    "maigret": "Maigret",
    "sherlock": "Sherlock",
    "holehe": "Holehe",
    "ghunt": "GHunt",
    "phone": "Номер телефону",
}


def render_report(
    query: str, query_type: str, results: list[ToolResult], reports_dir: Path
) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html.j2")
    html = template.render(
        query=query,
        query_type=query_type,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        results=results,
        tool_names=TOOL_NAMES,
    )

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_query = "".join(c if c.isalnum() else "_" for c in query)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"{timestamp}_{safe_query}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
```

- [ ] **Step 6: Run tests, verify they pass**

Run: `pytest tests/test_render.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add bot/report/ tests/test_render.py
git commit -m "feat: add Jinja2 HTML report renderer with tactical dark theme"
```

---

### Task 13: Inline keyboards

**Files:**
- Create: `bot/keyboards.py`
- Create: `tests/test_keyboards.py`

**Interfaces:**
- Produces: `bot.keyboards.main_menu(is_admin: bool) -> InlineKeyboardMarkup`, `bot.keyboards.admin_menu(access_mode: str, ghunt_enabled: bool) -> InlineKeyboardMarkup`, `bot.keyboards.users_list_menu(user_ids: list[int]) -> InlineKeyboardMarkup`

- [ ] **Step 1: Write the failing tests**

`tests/test_keyboards.py`:
```python
from bot.keyboards import admin_menu, main_menu, users_list_menu


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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_keyboards.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.keyboards'`

- [ ] **Step 3: Implement `bot/keyboards.py`**

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔍 Новий пошук", callback_data="search:new")],
        [InlineKeyboardButton(text="📄 Мої звіти", callback_data="reports:list")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="⚙️ Налаштування", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu(access_mode: str, ghunt_enabled: bool) -> InlineKeyboardMarkup:
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


def users_list_menu(user_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"❌ {uid}", callback_data=f"admin:deluser:{uid}")]
        for uid in user_ids
    ]
    rows.append([InlineKeyboardButton(text="➕ Додати", callback_data="admin:adduser")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_keyboards.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add bot/keyboards.py tests/test_keyboards.py
git commit -m "feat: add inline keyboard builders for main/admin menus"
```

---

### Task 14: `/start` handler + main menu navigation

**Files:**
- Create: `bot/handlers/__init__.py`
- Create: `bot/handlers/start.py`

**Interfaces:**
- Consumes: `bot.db.is_authorized`, `bot.db.get_setting`, `bot.keyboards.main_menu`, `bot.keyboards.admin_menu`
- Produces: `bot.handlers.start.router` (an `aiogram.Router` with `/start` command handler and `menu:main` / `admin:menu` callback handlers), registered in `bot/main.py` in Task 17

- [ ] **Step 1: Create `bot/handlers/__init__.py`** (empty file)

- [ ] **Step 2: Implement `bot/handlers/start.py`**

```python
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
```

- [ ] **Step 3: Manual verification**

This task wires aiogram routing and depends on a live `Bot`/`Dispatcher`, which is out of proportion to unit-test in isolation (aiogram's own test suite already covers dispatch correctness). Automated coverage for the logic it calls (`is_authorized`, `get_setting`, `main_menu`, `admin_menu`) already exists from Tasks 2 and 13. Verify this task manually once `bot/main.py` exists (Task 17):
1. Run the bot, send `/start` as a non-whitelisted user → expect "Доступ закрито" message, no keyboard.
2. Add yourself via `ADMIN_ID` in `.env`, send `/start` → expect main menu with all three buttons including "⚙️ Налаштування".
3. Press "⚙️ Налаштування" → expect admin menu with current mode/GHunt labels.
4. Press "⬅️ Назад" → expect main menu again.

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/__init__.py bot/handlers/start.py
git commit -m "feat: add /start handler and main/admin menu navigation"
```

---

### Task 15: Admin handlers (users, access mode, GHunt toggle)

**Files:**
- Create: `bot/handlers/admin.py`

**Interfaces:**
- Consumes: `bot.db.add_user`, `bot.db.remove_user`, `bot.db.list_users`, `bot.db.get_setting`, `bot.db.set_setting`, `bot.keyboards.users_list_menu`, `bot.keyboards.admin_menu`
- Produces: `bot.handlers.admin.router` (an `aiogram.Router`), `bot.handlers.admin.AdminStates` (a `StatesGroup` with `waiting_for_new_user_id`), registered in `bot/main.py` in Task 17

- [ ] **Step 1: Implement `bot/handlers/admin.py`**

```python
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
```

- [ ] **Step 2: Manual verification**

Same rationale as Task 14 — the underlying logic (`db.py`, `keyboards.py`) is already unit-tested; this task is aiogram wiring. Verify manually once `bot/main.py` exists (Task 17):
1. As admin, "⚙️ Налаштування" → "👥 Користувачі" → "➕ Додати" → send a numeric Telegram ID → expect confirmation and updated list.
2. Press ❌ next to that ID → expect it disappears from the list.
3. Press mode toggle button twice → expect label flips "Whitelist" ↔ "Відкритий" each time.
4. Press GHunt toggle button twice → expect label flips "Вимкнено" ↔ "Увімкнено" each time.
5. As a non-admin user, confirm none of these callbacks are reachable (no "⚙️ Налаштування" button shown) and that manually crafted admin callback_data (if triggered) responds with the "Тільки для адміністратора" alert.

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/admin.py
git commit -m "feat: add admin inline-button panel for users/mode/ghunt"
```

---

### Task 16: Search handler (FSM + orchestration + report delivery)

**Files:**
- Create: `bot/handlers/search.py`

**Interfaces:**
- Consumes: `bot.osint.detect.detect_query_type`, `bot.osint.orchestrator.run_tools_for_query`, `bot.report.render.render_report`, `bot.db.get_setting`, `bot.keyboards.main_menu`
- Produces: `bot.handlers.search.router` (an `aiogram.Router`), `bot.handlers.search.SearchStates` (a `StatesGroup` with `waiting_for_query`), `bot.handlers.search.active_requests: set[int]` (module-level, tracks in-progress users), registered in `bot/main.py` in Task 17

- [ ] **Step 1: Implement `bot/handlers/search.py`**

```python
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.db import get_setting
from bot.keyboards import main_menu
from bot.osint.detect import detect_query_type
from bot.osint.orchestrator import run_tools_for_query
from bot.report.render import render_report

router = Router(name="search")

REPORTS_DIR = Path("reports")

# In-process guard against a user firing a second search while their first
# one is still running. Single-process bot, so a plain in-memory set is
# sufficient; it does not need to survive a restart.
active_requests: set[int] = set()


class SearchStates(StatesGroup):
    waiting_for_query = State()


@router.callback_query(F.data == "search:new")
async def cb_search_new(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id in active_requests:
        await callback.answer("Зачекай, попередній запит ще виконується.", show_alert=True)
        return
    await state.set_state(SearchStates.waiting_for_query)
    await callback.message.edit_text("Надішли номер телефону, email або юзернейм:")
    await callback.answer()


@router.message(SearchStates.waiting_for_query)
async def on_query(
    message: Message, conn, admin_id: int, blackbird_dir: Path, state: FSMContext
) -> None:
    user_id = message.from_user.id
    if user_id in active_requests:
        await message.answer("Зачекай, попередній запит ще виконується.")
        return

    query = message.text.strip()
    query_type = detect_query_type(query)
    if query_type is None:
        await message.answer(
            "Не розпізнав запит. Надішли номер телефону (з +), email або юзернейм."
        )
        return

    active_requests.add(user_id)
    status_message = await message.answer("⏳ Виконується...")
    try:
        ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
        results = await run_tools_for_query(
            query, query_type, blackbird_dir=blackbird_dir, ghunt_enabled=ghunt_enabled
        )
        report_path = render_report(
            query, query_type, results, reports_dir=REPORTS_DIR / str(user_id)
        )
        await status_message.edit_text("✅ Готово, надсилаю звіт.")
        await message.answer_document(FSInputFile(report_path))
    finally:
        active_requests.discard(user_id)
        await state.clear()
        is_admin = user_id == admin_id
        await message.answer("Обери дію:", reply_markup=main_menu(is_admin))
```

- [ ] **Step 2: Manual verification**

The pure logic this handler drives (`detect_query_type`, `run_tools_for_query`, `render_report`) is already unit-tested in Tasks 3, 11, and 12; this task is aiogram FSM wiring plus the concurrency guard, which needs a live bot to exercise meaningfully. Verify manually once `bot/main.py` exists (Task 17):
1. "🔍 Новий пошук" → send your own username → expect "⏳ Виконується..." then a `.html` document with blackbird/maigret/sherlock cards.
2. Open the received `.html` file in a browser → confirm it renders the dark tactical theme with real results (or "Нічого не знайдено" / "НЕДОСТУПНО" where applicable).
3. Repeat with your own email → expect a holehe card (and a GHunt card if you enabled it and the address is gmail.com).
4. Repeat with your own phone number (with `+` and country code) → expect a single "Номер телефону" card with country/region/carrier/line type/timezones.
5. While one search is running, press "🔍 Новий пошук" and send another query immediately → expect "Зачекай, попередній запит ще виконується."
6. Send plain gibberish (e.g. `"???"`) as a query → expect the "Не розпізнав запит" message, no tools run.

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/search.py
git commit -m "feat: add search FSM handler orchestrating OSINT tools and report delivery"
```

---

### Task 17: Entry point + README

**Files:**
- Create: `bot/main.py`
- Create: `README.md`
- Create: `reports/.gitkeep`
- Create: `data/.gitkeep`

**Interfaces:**
- Consumes: `bot.config.load_config`, `bot.db.init_db`, `bot.handlers.start.router`, `bot.handlers.admin.router`, `bot.handlers.search.router`
- Produces: running process (no importable interface consumed by later tasks — this is the last task)

- [ ] **Step 1: Implement `bot/main.py`**

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.config import load_config
from bot.db import init_db
from bot.handlers import admin, search, start


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    config = load_config()

    conn = await init_db("data/bot.sqlite3")
    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(start.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(search.router)

    try:
        await dispatcher.start_polling(
            bot,
            conn=conn,
            admin_id=config.admin_id,
            blackbird_dir=config.blackbird_dir,
        )
    finally:
        await conn.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Create `reports/.gitkeep`** (empty file)

- [ ] **Step 3: Create `data/.gitkeep`** (empty file)

- [ ] **Step 4: Write `README.md`**

Document, in order:
1. Prerequisites: Python 3.11+, `git`, `pipx`.
2. `pip install -r requirements.txt`.
3. Clone blackbird separately: `git clone https://github.com/p1ngul1n0/blackbird` and `pip install -r blackbird/requirements.txt`, then set `BLACKBIRD_DIR` in `.env` to that clone's absolute path.
4. `pipx install sherlock-project` (sherlock's own installer recommends pipx over plain pip).
5. Copy `.env.example` to `.env`, fill in `BOT_TOKEN` (from @BotFather) and `ADMIN_ID` (your own Telegram numeric ID, e.g. from @userinfobot).
6. Optional GHunt: `pipx install ghunt`, then run `ghunt login` once and follow its GHunt Companion browser-extension instructions; only after that does the in-bot GHunt toggle do anything.
7. Run: `python -m bot.main`.
8. In Telegram, message the bot `/start`. As `ADMIN_ID` you always have access; use "⚙️ Налаштування" → "👥 Користувачі" → "➕ Додати" to let others in, or "🔓 Режим: Відкритий" to open it to anyone.
9. Running tests: `pytest`.

- [ ] **Step 5: Manual end-to-end verification**

1. Follow the README from a clean checkout (or as close to clean as practical) to confirm no missing step.
2. Run `python -m bot.main`, confirm it starts without exceptions and logs polling has started.
3. Run through the full manual verification checklists from Tasks 14, 15, and 16 against the live bot.

- [ ] **Step 6: Commit**

```bash
git add bot/main.py README.md reports/.gitkeep data/.gitkeep
git commit -m "feat: add bot entry point and installation README"
```

---

### Task 18: Report history ("Мої звіти")

**Files:**
- Modify: `bot/keyboards.py`
- Modify: `bot/handlers/start.py`
- Create: `tests/test_keyboards.py` (append a test to the existing file)

**Interfaces:**
- Consumes: `bot.handlers.search.REPORTS_DIR`
- Produces: `bot.keyboards.reports_list_menu(reports: list[Path]) -> InlineKeyboardMarkup`, extends `bot.handlers.start.router` with `reports:list` and `reports:send:<index>` callbacks

- [ ] **Step 1: Write the failing test**

Append to `tests/test_keyboards.py`:
```python
from pathlib import Path

from bot.keyboards import reports_list_menu


def test_reports_list_menu_one_button_per_report():
    reports = [Path("20260910_120000_mrmozozavr.html"), Path("20260909_090000_user_example_com.html")]
    markup = reports_list_menu(reports)
    callback_data = [b.callback_data for b in _flatten(markup)]
    assert "reports:send:0" in callback_data
    assert "reports:send:1" in callback_data
    assert "menu:main" in callback_data
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_keyboards.py -v`
Expected: FAIL with `ImportError: cannot import name 'reports_list_menu'`

- [ ] **Step 3: Add `reports_list_menu` to `bot/keyboards.py`**

Append to `bot/keyboards.py`:
```python
from pathlib import Path


def reports_list_menu(reports: list[Path]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=report.name, callback_data=f"reports:send:{i}")]
        for i, report in enumerate(reports)
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_keyboards.py -v`
Expected: 5 passed

- [ ] **Step 5: Add `reports:list` and `reports:send:<index>` handlers to `bot/handlers/start.py`**

Append to `bot/handlers/start.py` (add `from pathlib import Path` and `from bot.keyboards import reports_list_menu` to the existing imports, and `from aiogram.types import FSInputFile` alongside the existing `aiogram.types` import):
```python
REPORTS_DIR = Path("reports")


def _user_reports(user_id: int) -> list[Path]:
    user_dir = REPORTS_DIR / str(user_id)
    if not user_dir.exists():
        return []
    return sorted(user_dir.glob("*.html"), reverse=True)


@router.callback_query(F.data == "reports:list")
async def cb_reports_list(callback: CallbackQuery) -> None:
    reports = _user_reports(callback.from_user.id)
    if not reports:
        await callback.answer("Звітів ще немає.", show_alert=True)
        return
    await callback.message.edit_text(
        "Твої звіти:", reply_markup=reports_list_menu(reports)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reports:send:"))
async def cb_reports_send(callback: CallbackQuery) -> None:
    reports = _user_reports(callback.from_user.id)
    index = int(callback.data.removeprefix("reports:send:"))
    if index >= len(reports):
        await callback.answer("Файл більше не існує.", show_alert=True)
        return
    await callback.message.answer_document(FSInputFile(reports[index]))
    await callback.answer()
```

- [ ] **Step 6: Manual verification**

Same rationale as Tasks 14–16 — the listed-report logic (`_user_reports`, `reports_list_menu`) is a thin aiogram-wiring layer over already-tested pieces. Verify manually once `bot/main.py` exists (Task 17):
1. Run at least one search to completion (Task 16 flow) so a file exists under `reports/<your_id>/`.
2. From the main menu, press "📄 Мої звіти" → expect a list with one button per past report, newest first.
3. Press one → expect the bot to resend that exact `.html` file.
4. As a fresh user with no reports yet, press "📄 Мої звіти" → expect the "Звітів ще немає." alert, no list shown.

- [ ] **Step 7: Commit**

```bash
git add bot/keyboards.py bot/handlers/start.py tests/test_keyboards.py
git commit -m "feat: add report history browsing via inline buttons"
```

---

## Self-Review Notes

- **Spec coverage:** query detection (Task 3), all six tool integrations incl. exact verified CLI flags/paths (Tasks 4, 6–10), parallel dispatch by query type (Task 11), tactical-theme HTML report (Task 12), inline-button-only navigation incl. `/start` as the sole command (Tasks 13–16), whitelist/admin panel with add/remove/mode/GHunt toggle (Tasks 2, 15), concurrent-request guard (Task 16), report history browsing (Task 18) — all spec items now have a task.
- **Placeholder scan:** no TBD/TODO markers; every step has complete, runnable code or a concrete manual checklist (Tasks 14–18 use manual verification deliberately, with reasoning given, not as a shortcut).
- **Type consistency:** `ToolResult` (Task 3) used identically across every runner (Tasks 4, 6–10), orchestrator (Task 11), and renderer (Task 12). Item shape `{"label": str, "value": str}` held consistently everywhere items are produced or rendered. `Config` fields (`bot_token`, `admin_id`, `blackbird_dir`) match their usage in `main.py` (Task 17). `REPORTS_DIR` layout (`reports/<user_id>/*.html`) matches between Task 16 (writer) and Task 18 (reader).
