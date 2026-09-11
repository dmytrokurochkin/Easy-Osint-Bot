# Zero-Friction Bootstrap, Vendored Blackbird, 3-Language i18n Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `git clone` + `python main.py` (answering two prompts for `BOT_TOKEN`/`ADMIN_ID`) brings the bot to a fully working state with no other manual step, and every user can pick English/Ukrainian/Polish for everything they see (messages, keyboards, generated reports).

**Architecture:** Blackbird moves from a runtime `git clone` into vendored, tracked source (its own GPLv3 license kept intact) at a fixed path. A new `core/bootstrap.py`, run at the very top of `main.py`, replaces `scripts/setup.py`: it installs missing pip dependencies, interactively writes `.env` if absent, and best-effort installs GHunt via pipx (login stays manual — it's an interactive OAuth browser flow, not automatable). A new `locales.py` holds all translated strings behind `get_text(lang, key, **kwargs)`; a new `user_language` DB table stores each Telegram user's choice; `AuthMiddleware` loads it once per request and injects `lang` into aiogram's dependency-injection `data` dict so every handler receives it like `conn`/`admin_id` already do.

**Tech Stack:** Python 3.11+, aiogram 3, aiosqlite, Jinja2, pytest/pytest-asyncio (unchanged from the existing project).

**Spec:** `docs/superpowers/specs/2026-09-11-bootstrap-vendoring-i18n-design.md`

## Global Constraints

- Code/comments stay English; user-facing bot text is now multi-language via `locales.py` (no more hardcoded Ukrainian in handler/keyboard source — see repo-style conventions in `CLAUDE.md`).
- `blackbird/` keeps its own `LICENSE`/`README.md`/`docs/` untouched (GPLv3 attribution) — never strip them.
- `full pytest -q` must pass after every task before moving to the next.
- Router variables stay `<domain>_router`; keyboard factories stay `get_<what>_keyboard()` (existing repo-style convention).
- No new heavyweight i18n framework — the flat `TEXTS: dict[lang, dict[key, str]]` + `get_text()` pattern only.

---

### Task 1: Vendor blackbird into git

**Files:**
- Modify: `.gitignore`
- Delete: `blackbird/.git/` (directory)

**Interfaces:**
- Produces: `blackbird/` as ordinary tracked source under this repo (no separate clone step for anyone who `git clone`s this repo from now on).

- [ ] **Step 1: Remove blackbird's own git history**

```bash
rm -rf blackbird/.git
```

This makes `blackbird/` plain files instead of a nested git repo (a nested `.git/` would make `git add blackbird/` silently create a broken gitlink instead of tracking the files).

- [ ] **Step 2: Update `.gitignore` — un-ignore the source, keep ignoring its runtime output**

Replace the line `blackbird/` in `.gitignore` with:

```
blackbird/logs/
blackbird/results/
blackbird/__pycache__/
blackbird/**/__pycache__/
blackbird/.env
```

(Leave every other existing line in `.gitignore` untouched.)

- [ ] **Step 3: Verify what would be staged**

Run: `git add -A -- blackbird && git status --short -- blackbird | head -20`
Expected: a long list of `A` (added) lines for `blackbird/blackbird.py`, `blackbird/src/...`, `blackbird/data/...`, `blackbird/docs/...`, `blackbird/LICENSE`, `blackbird/README.md`, etc. — and **no** lines for `blackbird/logs/`, `blackbird/results/`, `blackbird/.env`, or any `__pycache__/`.

If any runtime/log/cache path shows up as staged, fix the `.gitignore` patterns from Step 2 and re-run `git reset -- blackbird && git add -A -- blackbird` before continuing.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: vendor blackbird source directly into the repo (GPLv3 kept intact)"
```

---

### Task 2: Drop `BLACKBIRD_DIR` from configuration

**Files:**
- Modify: `core/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Produces: `core.config.BLACKBIRD_DIR: Path` (module-level constant), `Config` dataclass with `blackbird_dir` defaulting to it, `load_config(env=None)` no longer requiring `BLACKBIRD_DIR` in the environment.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_config.py` with:

```python
import pytest
from pathlib import Path
from core.config import load_config, ConfigError, Config, BLACKBIRD_DIR


def test_load_config_success():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "111222333"}
    config = load_config(env)
    assert config == Config(
        bot_token="123:ABC",
        admin_id=111222333,
        blackbird_dir=BLACKBIRD_DIR,
    )


def test_load_config_missing_bot_token():
    env = {"ADMIN_ID": "1"}
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(env)


def test_load_config_missing_admin_id():
    env = {"BOT_TOKEN": "123:ABC"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_load_config_admin_id_not_integer():
    env = {"BOT_TOKEN": "123:ABC", "ADMIN_ID": "not-a-number"}
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_config(env)


def test_blackbird_dir_points_at_vendored_directory():
    assert BLACKBIRD_DIR.name == "blackbird"
    assert (BLACKBIRD_DIR / "blackbird.py").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: `ImportError: cannot import name 'BLACKBIRD_DIR' from 'core.config'` (or similar collection error).

- [ ] **Step 3: Rewrite `core/config.py`**

```python
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


# blackbird is vendored directly in this repo (see blackbird/), not a
# separately-cloned tool the user points at via .env, so its path is a
# fixed constant, not configuration.
BLACKBIRD_DIR = Path(__file__).resolve().parent.parent / "blackbird"


@dataclass
class Config:
    bot_token: str
    admin_id: int
    blackbird_dir: Path = BLACKBIRD_DIR


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

    return Config(bot_token=bot_token, admin_id=admin_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add core/config.py tests/test_config.py
git commit -m "refactor: drop BLACKBIRD_DIR from .env, use a fixed vendored path"
```

---

### Task 3: Merge blackbird's own dependencies into `requirements.txt`

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: a single `requirements.txt` that, once installed, satisfies both the bot's own imports and vendored blackbird's imports (blackbird runs as a subprocess script under the same interpreter — see `osint/runners/blackbird.py` — so its dependencies must live in the same environment).

- [ ] **Step 1: Rewrite `requirements.txt`**

```
aiogram>=3.10,<4
aiosqlite>=0.20
python-dotenv>=1.0
phonenumbers>=8.13
maigret
holehe
sherlock-project
Jinja2>=3.1
# blackbird (vendored in blackbird/) runs as a subprocess under this same
# interpreter rather than as a pip package - these are its own runtime
# dependencies, merged in so one `pip install -r requirements.txt` covers
# everything.
aiohttp>=3.12
rich>=14.0
chardet>=5.2
requests>=2.32
reportlab>=4.4
pillow>=11.0
```

- [ ] **Step 2: Verify it installs cleanly**

Run: `pip install -r requirements.txt`
Expected: completes without dependency-resolution errors (pip reports "Successfully installed ..." or "Requirement already satisfied" for every line, no `ERROR: pip's dependency resolver...` conflict message).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: merge vendored blackbird's dependencies into requirements.txt"
```

---

### Task 4: `core/bootstrap.py` — zero-friction startup

**Files:**
- Create: `core/bootstrap.py`
- Create: `tests/test_bootstrap.py`
- Delete: `scripts/setup.py`
- Delete: `scripts/` (directory, now empty)

**Interfaces:**
- Consumes: `core.config.Config`, `core.config.load_config` (Task 2).
- Produces: `core.bootstrap.ensure_ready() -> Config` — the single entry point `main.py` calls before anything else.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bootstrap.py`:

```python
import sys

import core.bootstrap as bootstrap


def test_ensure_env_file_prompts_when_missing(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    monkeypatch.setattr(bootstrap, "ENV_PATH", env_path)

    answers = iter(["123:ABC", "999"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    bootstrap._ensure_env_file()

    content = env_path.read_text(encoding="utf-8")
    assert "BOT_TOKEN=123:ABC" in content
    assert "ADMIN_ID=999" in content


def test_ensure_env_file_skips_when_present(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("BOT_TOKEN=existing\nADMIN_ID=1\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "ENV_PATH", env_path)

    def _fail_input(prompt):
        raise AssertionError("should not prompt when .env already exists")

    monkeypatch.setattr("builtins.input", _fail_input)

    bootstrap._ensure_env_file()

    assert env_path.read_text(encoding="utf-8") == "BOT_TOKEN=existing\nADMIN_ID=1\n"


def test_ensure_dependencies_installs_when_module_missing(monkeypatch):
    monkeypatch.setattr(bootstrap.importlib.util, "find_spec", lambda name: None)
    calls = []
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    bootstrap._ensure_dependencies()

    assert len(calls) == 1
    assert calls[0][:4] == [sys.executable, "-m", "pip", "install"]


def test_ensure_dependencies_skips_when_all_present(monkeypatch):
    monkeypatch.setattr(bootstrap.importlib.util, "find_spec", lambda name: object())

    def _fail_run(cmd, **kwargs):
        raise AssertionError("should not install when all modules are present")

    monkeypatch.setattr(bootstrap.subprocess, "run", _fail_run)

    bootstrap._ensure_dependencies()


def test_ensure_ghunt_skips_when_already_installed(monkeypatch):
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: "/usr/bin/ghunt")

    def _fail_run(cmd, **kwargs):
        raise AssertionError("should not install when ghunt is already present")

    monkeypatch.setattr(bootstrap.subprocess, "run", _fail_run)

    bootstrap._ensure_ghunt()


def test_ensure_ghunt_installs_via_pipx_when_missing(monkeypatch):
    which_map = {"ghunt": None, "pipx": "/usr/bin/pipx"}
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: which_map.get(name))
    calls = []
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    bootstrap._ensure_ghunt()

    assert any("ghunt" in cmd for cmd in calls)


def test_ensure_ready_calls_all_steps_in_order_and_returns_config(monkeypatch):
    calls = []
    monkeypatch.setattr(bootstrap, "_ensure_dependencies", lambda: calls.append("deps"))
    monkeypatch.setattr(bootstrap, "_ensure_env_file", lambda: calls.append("env"))
    monkeypatch.setattr(bootstrap, "load_dotenv", lambda: calls.append("load_dotenv"))
    monkeypatch.setattr(bootstrap, "_ensure_ghunt", lambda: calls.append("ghunt"))
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("ADMIN_ID", "1")

    config = bootstrap.ensure_ready()

    assert calls == ["deps", "env", "load_dotenv", "ghunt"]
    assert config.bot_token == "123:ABC"
    assert config.admin_id == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bootstrap.py -v`
Expected: `ModuleNotFoundError: No module named 'core.bootstrap'`.

- [ ] **Step 3: Create `core/bootstrap.py`**

```python
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.config import Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"

# A representative subset is enough: if the project has never been set up,
# aiogram itself will be missing and the resulting `pip install -r
# requirements.txt` brings in everything else (maigret/holehe/sherlock
# included) in one pass - this list doesn't need to be exhaustive.
REQUIRED_MODULES = ["aiogram", "aiosqlite", "dotenv", "phonenumbers", "jinja2", "aiohttp", "rich", "chardet"]


def _ensure_dependencies() -> None:
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if not missing:
        return
    print(f"Встановлюю відсутні залежності: {', '.join(missing)}...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)],
        check=True,
    )


def _ensure_env_file() -> None:
    if ENV_PATH.exists():
        return
    print("Файл .env не знайдено. Потрібні два значення з Telegram:")
    bot_token = input("BOT_TOKEN (від @BotFather, https://t.me/botfather): ").strip()
    admin_id = input("ADMIN_ID (твій числовий ID від @userinfobot, https://t.me/userinfobot): ").strip()
    ENV_PATH.write_text(f"BOT_TOKEN={bot_token}\nADMIN_ID={admin_id}\n", encoding="utf-8")
    print(f"Записано {ENV_PATH}")


def _ensure_ghunt() -> None:
    if shutil.which("ghunt") is not None:
        return
    print("GHunt не знайдено — встановлюю через pipx...")
    if shutil.which("pipx") is None:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pipx"], check=True)
            subprocess.run([sys.executable, "-m", "pipx", "ensurepath"], check=True)
        except subprocess.CalledProcessError:
            print("Не вдалося автоматично встановити pipx. Постав вручну: pip install --user pipx")
            return
    try:
        subprocess.run([sys.executable, "-m", "pipx", "install", "ghunt"], check=True)
    except subprocess.CalledProcessError:
        print("GHunt вже встановлений або встановлення пропущено (перевір: pipx list).")
    print("Якщо це перший запуск GHunt — постав логін вручну: ghunt login")


def ensure_ready() -> Config:
    """Idempotent - safe to call on every startup. Skips whatever is
    already satisfied, so a second/third/nth run is nearly instant."""
    _ensure_dependencies()
    _ensure_env_file()
    load_dotenv()
    _ensure_ghunt()
    return load_config()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bootstrap.py -v`
Expected: 7 passed.

- [ ] **Step 5: Wire into `main.py`**

Replace the top of `main.py` (everything before `async def main`) with:

```python
import asyncio
import logging

from core.bootstrap import ensure_ready
from core.loader import create_bot, create_dispatcher
from database import init_db
from handlers.admin import admin_router
from handlers.search import search_router
from handlers.start import start_router
from middlewares.auth import AuthMiddleware
```

(Drops the now-redundant `load_dotenv`/`load_config` imports and calls inside `main()` — `ensure_ready()` does both. `handlers.language` and its `language_router` are wired in Task 9, not here.)

Then, inside `async def main() -> None:`, replace the first three lines
(`logging.basicConfig(...)`, `load_dotenv()`, `config = load_config()`) with:

```python
    logging.basicConfig(level=logging.INFO)
    config = ensure_ready()
```

- [ ] **Step 6: Delete the now-redundant installer**

```bash
rm -rf scripts
```

- [ ] **Step 7: Update `README.md` and `scripts/setup.py` references**

Search for any remaining mention of `scripts/setup.py` outside this plan/spec:

Run: `grep -rn "scripts/setup.py\|scripts\.setup" --include="*.py" --include="*.md" .`
Expected: no matches in `README.md`, `CLAUDE.md`, or any `.py` file (README/CLAUDE.md content is rewritten in Tasks 15-16; if this grep still finds something outside those two files, fix it now).

- [ ] **Step 8: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (bootstrap's own 7 plus every pre-existing test, since nothing else changed behavior yet).

- [ ] **Step 9: Commit**

```bash
git add core/bootstrap.py tests/test_bootstrap.py main.py
git add -A -- scripts
git commit -m "feat: auto-bootstrap deps, .env, and GHunt on every main.py startup"
```

---

### Task 5: `locales.py` — the translation table

**Files:**
- Create: `locales.py`
- Create: `tests/test_locales.py`

**Interfaces:**
- Produces: `locales.DEFAULT_LANGUAGE: str`, `locales.SUPPORTED_LANGUAGES: dict[str, str]`, `locales.get_text(lang: str, key: str, **kwargs) -> str`. Every later task (keyboards, handlers, middleware, report) consumes `get_text` and the exact key names defined here.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_locales.py`:

```python
from locales import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TEXTS, get_text


def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en"


def test_supported_languages_are_exactly_en_uk_pl():
    assert set(SUPPORTED_LANGUAGES) == {"en", "uk", "pl"}


def test_every_language_defines_every_key():
    all_keys = set(TEXTS[DEFAULT_LANGUAGE])
    for lang in SUPPORTED_LANGUAGES:
        assert set(TEXTS[lang]) == all_keys, f"{lang} is missing or has extra keys"


def test_get_text_returns_requested_language():
    assert get_text("uk", "choose_action") == "Обери дію:"
    assert get_text("pl", "choose_action") == "Wybierz akcję:"
    assert get_text("en", "choose_action") == "Choose an action:"


def test_get_text_falls_back_to_english_for_unsupported_language():
    assert get_text("fr", "choose_action") == get_text("en", "choose_action")


def test_get_text_falls_back_to_raw_key_when_missing_everywhere():
    assert get_text("en", "no_such_key") == "no_such_key"


def test_get_text_formats_kwargs():
    assert get_text("en", "report_title", query="mrmozozavr") == "OSINT Report: mrmozozavr"
    assert get_text("uk", "report_title", query="mrmozozavr") == "OSINT Звіт: mrmozozavr"
    assert get_text("pl", "report_title", query="mrmozozavr") == "Raport OSINT: mrmozozavr"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_locales.py -v`
Expected: `ModuleNotFoundError: No module named 'locales'`.

- [ ] **Step 3: Create `locales.py`**

```python
DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "uk": "Українська",
    "pl": "Polski",
}

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "btn_new_search": "🔍 New search",
        "btn_my_reports": "📄 My reports",
        "btn_settings": "⚙️ Settings",
        "btn_users": "👥 Users",
        "btn_back": "⬅️ Back",
        "btn_add": "➕ Add",
        "admin_mode_open": "🔓 Mode: Open",
        "admin_mode_whitelist": "🔒 Mode: Whitelist",
        "admin_ghunt_on": "GHunt: 🟢 Enabled",
        "admin_ghunt_off": "GHunt: 🔴 Disabled",
        "admin_only": "Admins only.",
        "users_list_header": "Users with access:",
        "users_list_empty": "The list is empty.",
        "user_deleted": "Removed.",
        "prompt_new_user_id": "Send the Telegram ID of the user to add:",
        "user_id_not_text": "ID must be a text message with a number. Try again:",
        "user_id_not_digit": "ID must be a number. Try again:",
        "user_added_header": "User added.\n\nUsers with access:",
        "settings_title": "Settings:",
        "choose_action": "Choose an action:",
        "no_reports_yet": "No reports yet.",
        "your_reports": "Your reports:",
        "file_no_longer_exists": "The file no longer exists.",
        "search_in_progress": "Wait, the previous request is still running.",
        "prompt_query": "Send a phone number, email, or username:",
        "please_send_text": "Please send a text message.",
        "query_not_recognized": "Couldn't recognize the request. Send a phone number (with +), email, or username.",
        "search_running": "⏳ Running...",
        "search_done": "✅ Done, sending the report.",
        "search_error": "❌ An error occurred while running the search.",
        "unauthorized_message": "Access denied. Contact the bot administrator.",
        "unauthorized_callback": "Access denied.",
        "choose_language": "Choose your language:",
        "report_title": "OSINT Report: {query}",
        "report_status_ok": "OK",
        "report_status_unavailable": "UNAVAILABLE",
        "report_nothing_found": "Nothing found.",
        "report_tool_unavailable": "Tool unavailable.",
        "report_footer": "Generated by OSINT bot",
        "tool_phone": "Phone number",
        "query_type_email": "Email",
        "query_type_phone": "Phone",
        "query_type_username": "Username",
    },
    "uk": {
        "btn_new_search": "🔍 Новий пошук",
        "btn_my_reports": "📄 Мої звіти",
        "btn_settings": "⚙️ Налаштування",
        "btn_users": "👥 Користувачі",
        "btn_back": "⬅️ Назад",
        "btn_add": "➕ Додати",
        "admin_mode_open": "🔓 Режим: Відкритий",
        "admin_mode_whitelist": "🔒 Режим: Whitelist",
        "admin_ghunt_on": "GHunt: 🟢 Увімкнено",
        "admin_ghunt_off": "GHunt: 🔴 Вимкнено",
        "admin_only": "Тільки для адміністратора.",
        "users_list_header": "Користувачі з доступом:",
        "users_list_empty": "Список порожній.",
        "user_deleted": "Видалено.",
        "prompt_new_user_id": "Надішли Telegram ID користувача, якого додати:",
        "user_id_not_text": "ID має бути текстовим повідомленням із числом. Спробуй ще раз:",
        "user_id_not_digit": "ID має бути числом. Спробуй ще раз:",
        "user_added_header": "Користувача додано.\n\nКористувачі з доступом:",
        "settings_title": "Налаштування:",
        "choose_action": "Обери дію:",
        "no_reports_yet": "Звітів ще немає.",
        "your_reports": "Твої звіти:",
        "file_no_longer_exists": "Файл більше не існує.",
        "search_in_progress": "Зачекай, попередній запит ще виконується.",
        "prompt_query": "Надішли номер телефону, email або юзернейм:",
        "please_send_text": "Будь ласка, надішли текстове повідомлення.",
        "query_not_recognized": "Не розпізнав запит. Надішли номер телефону (з +), email або юзернейм.",
        "search_running": "⏳ Виконується...",
        "search_done": "✅ Готово, надсилаю звіт.",
        "search_error": "❌ Сталася помилка під час виконання пошуку.",
        "unauthorized_message": "Доступ закрито. Звернись до адміністратора бота.",
        "unauthorized_callback": "Доступ закрито.",
        "choose_language": "Обери мову:",
        "report_title": "OSINT Звіт: {query}",
        "report_status_ok": "ОК",
        "report_status_unavailable": "НЕДОСТУПНО",
        "report_nothing_found": "Нічого не знайдено.",
        "report_tool_unavailable": "Інструмент недоступний.",
        "report_footer": "Згенеровано OSINT-ботом",
        "tool_phone": "Номер телефону",
        "query_type_email": "Email",
        "query_type_phone": "Телефон",
        "query_type_username": "Юзернейм",
    },
    "pl": {
        "btn_new_search": "🔍 Nowe wyszukiwanie",
        "btn_my_reports": "📄 Moje raporty",
        "btn_settings": "⚙️ Ustawienia",
        "btn_users": "👥 Użytkownicy",
        "btn_back": "⬅️ Wstecz",
        "btn_add": "➕ Dodaj",
        "admin_mode_open": "🔓 Tryb: Otwarty",
        "admin_mode_whitelist": "🔒 Tryb: Whitelist",
        "admin_ghunt_on": "GHunt: 🟢 Włączony",
        "admin_ghunt_off": "GHunt: 🔴 Wyłączony",
        "admin_only": "Tylko dla administratora.",
        "users_list_header": "Użytkownicy z dostępem:",
        "users_list_empty": "Lista jest pusta.",
        "user_deleted": "Usunięto.",
        "prompt_new_user_id": "Wyślij Telegram ID użytkownika do dodania:",
        "user_id_not_text": "ID musi być wiadomością tekstową z liczbą. Spróbuj ponownie:",
        "user_id_not_digit": "ID musi być liczbą. Spróbuj ponownie:",
        "user_added_header": "Użytkownik dodany.\n\nUżytkownicy z dostępem:",
        "settings_title": "Ustawienia:",
        "choose_action": "Wybierz akcję:",
        "no_reports_yet": "Nie ma jeszcze raportów.",
        "your_reports": "Twoje raporty:",
        "file_no_longer_exists": "Plik już nie istnieje.",
        "search_in_progress": "Poczekaj, poprzednie żądanie jeszcze się wykonuje.",
        "prompt_query": "Wyślij numer telefonu, e-mail lub nazwę użytkownika:",
        "please_send_text": "Wyślij wiadomość tekstową.",
        "query_not_recognized": "Nie rozpoznano żądania. Wyślij numer telefonu (z +), e-mail lub nazwę użytkownika.",
        "search_running": "⏳ Trwa wykonywanie...",
        "search_done": "✅ Gotowe, wysyłam raport.",
        "search_error": "❌ Wystąpił błąd podczas wyszukiwania.",
        "unauthorized_message": "Dostęp zablokowany. Skontaktuj się z administratorem bota.",
        "unauthorized_callback": "Dostęp zablokowany.",
        "choose_language": "Wybierz język:",
        "report_title": "Raport OSINT: {query}",
        "report_status_ok": "OK",
        "report_status_unavailable": "NIEDOSTĘPNY",
        "report_nothing_found": "Nic nie znaleziono.",
        "report_tool_unavailable": "Narzędzie niedostępne.",
        "report_footer": "Wygenerowano przez bota OSINT",
        "tool_phone": "Numer telefonu",
        "query_type_email": "E-mail",
        "query_type_phone": "Telefon",
        "query_type_username": "Nazwa użytkownika",
    },
}


def get_text(lang: str, key: str, **kwargs) -> str:
    """Look up TEXTS[lang][key]; fall back to English, then to the raw key
    itself if even English is missing it - a missing translation must
    never crash a handler. Formats with **kwargs when given."""
    language_texts = TEXTS.get(lang, TEXTS[DEFAULT_LANGUAGE])
    template = language_texts.get(key) or TEXTS[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**kwargs) if kwargs else template
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_locales.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add locales.py tests/test_locales.py
git commit -m "feat: add locales.py with English/Ukrainian/Polish translation tables"
```

---

### Task 6: Per-user language storage in `database.py`

**Files:**
- Modify: `database.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Consumes: `locales.DEFAULT_LANGUAGE` (Task 5).
- Produces: `database.get_user_language(conn, telegram_id) -> str`, `database.set_user_language(conn, telegram_id, language) -> None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_db.py` (add `get_user_language, set_user_language` to the existing `from database import (...)` block, then add):

```python
async def test_get_user_language_defaults_to_english_when_unset(conn):
    assert await get_user_language(conn, 42) == "en"


async def test_set_and_get_user_language_roundtrip(conn):
    await set_user_language(conn, 42, "uk")
    assert await get_user_language(conn, 42) == "uk"


async def test_set_user_language_overwrites_previous_choice(conn):
    await set_user_language(conn, 42, "uk")
    await set_user_language(conn, 42, "pl")
    assert await get_user_language(conn, 42) == "pl"


async def test_user_language_is_independent_of_whitelist(conn):
    """A user (including the admin) never needs to be in the `users`
    whitelist table to have a language preference - they're unrelated."""
    await set_user_language(conn, 999, "pl")
    assert await get_user_language(conn, 999) == "pl"
    assert 999 not in await list_users(conn)
```

(`list_users` is already imported in `tests/test_db.py`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -v`
Expected: `ImportError: cannot import name 'get_user_language' from 'database'`.

- [ ] **Step 3: Modify `database.py`**

Add the new table to `SCHEMA` (append inside the triple-quoted string, after the existing `settings` table):

```python
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

CREATE TABLE IF NOT EXISTS user_language (
    telegram_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'en'
);
"""
```

Add the import at the top of the file:

```python
import aiosqlite

from locales import DEFAULT_LANGUAGE
```

Append these two functions at the end of the file:

```python
async def get_user_language(conn: aiosqlite.Connection, telegram_id: int) -> str:
    cursor = await conn.execute(
        "SELECT language FROM user_language WHERE telegram_id = ?", (telegram_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else DEFAULT_LANGUAGE


async def set_user_language(conn: aiosqlite.Connection, telegram_id: int, language: str) -> None:
    await conn.execute(
        "INSERT INTO user_language (telegram_id, language) VALUES (?, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET language = excluded.language",
        (telegram_id, language),
    )
    await conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: all `test_db.py` tests pass (existing + 4 new).

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_db.py
git commit -m "feat: store per-user language preference in a new user_language table"
```

---

### Task 7: Inject `lang` via `AuthMiddleware`

**Files:**
- Modify: `middlewares/auth.py`
- Modify: `tests/test_middlewares.py`

**Interfaces:**
- Consumes: `database.get_user_language` (Task 6), `locales.get_text` (Task 5).
- Produces: every handler downstream of `AuthMiddleware` receives `lang: str` via aiogram DI (same mechanism as the existing `conn`/`admin_id` parameters), for both authorized and rejected requests.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_middlewares.py` with:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, User

from database import add_user, init_db, set_user_language
from middlewares.auth import AuthMiddleware


@pytest.fixture
async def conn():
    connection = await init_db(":memory:")
    yield connection
    await connection.close()


def _fake_callback(user_id: int) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=user_id, is_bot=False, first_name="X")
    callback.answer = AsyncMock()
    return callback


def _fake_message(user_id: int) -> Message:
    message = MagicMock(spec=Message)
    message.from_user = User(id=user_id, is_bot=False, first_name="X")
    message.answer = AsyncMock()
    return message


async def test_unauthorized_callback_is_blocked_and_handler_not_called(conn):
    handler = AsyncMock()
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_not_called()
    callback.answer.assert_awaited_once_with("Access denied.", show_alert=True)
    assert result is None


async def test_unauthorized_message_is_blocked_and_handler_not_called(conn):
    handler = AsyncMock()
    message = _fake_message(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": message.from_user}

    result = await AuthMiddleware()(handler, message, data)

    handler.assert_not_called()
    message.answer.assert_awaited_once_with("Access denied. Contact the bot administrator.")
    assert result is None


async def test_unauthorized_rejection_is_localized(conn):
    await set_user_language(conn, 42, "uk")
    handler = AsyncMock()
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    await AuthMiddleware()(handler, callback, data)

    callback.answer.assert_awaited_once_with("Доступ закрито.", show_alert=True)


async def test_admin_is_always_authorized_and_handler_runs(conn):
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=1)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_awaited_once_with(callback, data)
    callback.answer.assert_not_called()
    assert result == "handled"


async def test_whitelisted_user_is_authorized_and_handler_runs(conn):
    await add_user(conn, telegram_id=42, added_by=1)
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_awaited_once_with(callback, data)
    assert result == "handled"


async def test_lang_is_injected_into_data_defaulting_to_english(conn):
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=1)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    await AuthMiddleware()(handler, callback, data)

    assert data["lang"] == "en"


async def test_lang_reflects_users_saved_choice(conn):
    await set_user_language(conn, 1, "pl")
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=1)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    await AuthMiddleware()(handler, callback, data)

    assert data["lang"] == "pl"


async def test_removed_user_is_reauthorized_out_on_next_request(conn):
    """Regression test for the core finding: a user who was once
    whitelisted and then removed by the admin must be blocked on their
    very next request (e.g. pressing a button on an old cached message),
    not just on their next /start."""
    from database import remove_user

    await add_user(conn, telegram_id=42, added_by=1)
    handler = AsyncMock(return_value="handled")
    callback = _fake_callback(user_id=42)
    data = {"conn": conn, "admin_id": 1, "event_from_user": callback.from_user}

    result = await AuthMiddleware()(handler, callback, data)
    assert result == "handled"

    await remove_user(conn, 42)

    handler.reset_mock()
    callback.answer.reset_mock()
    result = await AuthMiddleware()(handler, callback, data)

    handler.assert_not_called()
    callback.answer.assert_awaited_once_with("Access denied.", show_alert=True)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_middlewares.py -v`
Expected: `test_lang_is_injected_into_data_defaulting_to_english` and `test_lang_reflects_users_saved_choice` fail with `KeyError: 'lang'`; the two "Access denied" assertions fail on the old Ukrainian text (still hardcoded at this point).

- [ ] **Step 3: Rewrite `middlewares/auth.py`**

```python
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database import get_user_language, is_authorized
from locales import get_text

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Outer middleware that re-checks whitelist/admin authorization on every
    event, not just on /start, and loads the requesting user's saved
    language preference into `data["lang"]` for every downstream handler.

    Without the auth re-check, a user who was whitelisted once (or used the
    bot while access_mode was "open") keeps a main-menu message in their
    chat with live inline buttons. Telegram lets those buttons be pressed
    forever, regardless of what happens to the user's authorization
    afterwards - so without a re-check here, removing a user via the admin
    panel (or flipping access_mode back to "whitelist") would be purely
    cosmetic.

    Must be registered as an OUTER middleware (not an inner/handler
    middleware) so it runs before FSM state/data is loaded and before the
    wrapped handler executes at all - an unauthorized user must never reach
    handler code.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        conn = data.get("conn")
        admin_id = data.get("admin_id")
        user = data.get("event_from_user")

        if conn is None or admin_id is None or user is None:
            # Nothing to authorize against (should not happen in normal
            # polling setup, since conn/admin_id are passed to
            # start_polling and event_from_user is populated by aiogram's
            # own UserContextMiddleware before router-level middlewares
            # run) - fail open to the handler rather than break unrelated
            # event types.
            return await handler(event, data)

        lang = await get_user_language(conn, user.id)
        data["lang"] = lang

        authorized = await is_authorized(conn, user.id, admin_id)
        if authorized:
            return await handler(event, data)

        logger.info("Blocked unauthorized access attempt by user_id=%s", user.id)

        if isinstance(event, CallbackQuery):
            await event.answer(get_text(lang, "unauthorized_callback"), show_alert=True)
        elif isinstance(event, Message):
            await event.answer(get_text(lang, "unauthorized_message"))
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_middlewares.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add middlewares/auth.py tests/test_middlewares.py
git commit -m "feat: inject per-user lang into every request via AuthMiddleware"
```

---

### Task 8: Localize `keyboards/inline.py` + add the language picker

**Files:**
- Modify: `keyboards/inline.py`
- Modify: `tests/test_keyboards.py`

**Interfaces:**
- Consumes: `locales.get_text`, `locales.SUPPORTED_LANGUAGES` (Task 5).
- Produces: `get_main_menu_keyboard(is_admin, lang)`, `get_admin_menu_keyboard(access_mode, ghunt_enabled, lang)`, `get_users_list_keyboard(user_ids, lang)`, `get_reports_list_keyboard(reports, lang)` (all gain a `lang` parameter), plus new `get_language_menu_keyboard(current: str)`.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_keyboards.py` with:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: `TypeError: get_main_menu_keyboard() missing 1 required positional argument: 'lang'` (and `ImportError` for `get_language_menu_keyboard`).

- [ ] **Step 3: Rewrite `keyboards/inline.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add keyboards/inline.py tests/test_keyboards.py
git commit -m "feat: localize keyboard labels and add the language picker keyboard"
```

---

### Task 9: `handlers/language.py` — the language switcher

**Files:**
- Create: `handlers/language.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `database.set_user_language` (Task 6), `keyboards.inline.get_language_menu_keyboard`, `keyboards.inline.get_main_menu_keyboard` (Task 8), `locales.get_text`, `locales.SUPPORTED_LANGUAGES` (Task 5).
- Produces: `handlers.language.language_router` (registered in `main.py` alongside `start_router`/`admin_router`/`search_router`, with `AuthMiddleware` attached the same way).

- [ ] **Step 1: Create `handlers/language.py`**

```python
from aiogram import F, Router
from aiogram.types import CallbackQuery

from database import set_user_language
from keyboards.inline import get_language_menu_keyboard, get_main_menu_keyboard
from locales import SUPPORTED_LANGUAGES, get_text

language_router = Router(name="language")


@language_router.callback_query(F.data == "lang:menu")
async def cb_language_menu(callback: CallbackQuery, lang: str) -> None:
    await callback.message.edit_text(
        get_text(lang, "choose_language"), reply_markup=get_language_menu_keyboard(lang)
    )
    await callback.answer()


@language_router.callback_query(F.data.startswith("lang:set:"))
async def cb_set_language(callback: CallbackQuery, conn, admin_id: int) -> None:
    new_lang = callback.data.removeprefix("lang:set:")
    if new_lang not in SUPPORTED_LANGUAGES:
        await callback.answer()
        return
    await set_user_language(conn, callback.from_user.id, new_lang)
    is_admin = callback.from_user.id == admin_id
    await callback.message.edit_text(
        get_text(new_lang, "choose_action"),
        reply_markup=get_main_menu_keyboard(is_admin, new_lang),
    )
    await callback.answer()
```

Note: `cb_set_language` deliberately does not take a `lang: str` parameter — it must render the *new* language the user just picked, not the stale one `AuthMiddleware` loaded from the DB before this handler updated it.

- [ ] **Step 2: Register `language_router` in `main.py`**

In `main.py`, add to the imports:

```python
from handlers.language import language_router
```

In `async def main()`, extend the middleware-registration loop and the router-inclusion calls to include it:

```python
    for router in (start_router, admin_router, search_router, language_router):
        router.message.outer_middleware(auth_middleware)
        router.callback_query.outer_middleware(auth_middleware)

    dispatcher.include_router(start_router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(search_router)
    dispatcher.include_router(language_router)
```

- [ ] **Step 3: Sanity-import the full app**

Run: `python -c "import main; print('main.py imports OK')"`
Expected: `main.py imports OK` (proves `language_router` wiring has no import errors; this doesn't start the bot).

- [ ] **Step 4: Commit**

```bash
git add handlers/language.py main.py
git commit -m "feat: add the per-user language switcher (handlers/language.py)"
```

---

### Task 10: Localize `handlers/start.py`

**Files:**
- Modify: `handlers/start.py`

**Interfaces:**
- Consumes: `locales.get_text` (Task 5), the now-`lang`-aware `keyboards.inline` factories (Task 8).
- Produces: every handler in this router gains a `lang: str` parameter.

- [ ] **Step 1: Rewrite `handlers/start.py`**

```python
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import get_setting
from keyboards.inline import get_admin_menu_keyboard, get_main_menu_keyboard, get_reports_list_keyboard
from locales import get_text

start_router = Router(name="start")


@start_router.message(CommandStart())
async def cmd_start(message: Message, admin_id: int, lang: str) -> None:
    # Authorization itself is enforced by AuthMiddleware (registered as an
    # outer middleware on this router in main.py), which runs before
    # this handler and short-circuits unauthorized requests.
    is_admin = message.from_user.id == admin_id
    await message.answer(get_text(lang, "choose_action"), reply_markup=get_main_menu_keyboard(is_admin, lang))


@start_router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, admin_id: int, lang: str) -> None:
    is_admin = callback.from_user.id == admin_id
    await callback.message.edit_text(
        get_text(lang, "choose_action"), reply_markup=get_main_menu_keyboard(is_admin, lang)
    )
    await callback.answer()


@start_router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, conn, admin_id: int, lang: str) -> None:
    if callback.from_user.id != admin_id:
        await callback.answer(get_text(lang, "admin_only"), show_alert=True)
        return
    access_mode = await get_setting(conn, "access_mode")
    ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
    await callback.message.edit_text(
        get_text(lang, "settings_title"),
        reply_markup=get_admin_menu_keyboard(access_mode, ghunt_enabled, lang),
    )
    await callback.answer()


REPORTS_DIR = Path("reports")

# Reports persist forever by design (per spec), so a heavy user's history
# can grow without bound. Telegram's InlineKeyboardMarkup has hard limits
# on button/row counts, so the report list must be capped rather than
# building one row per report ever generated.
MAX_REPORTS_SHOWN = 20


def _user_reports(user_id: int) -> list[Path]:
    user_dir = REPORTS_DIR / str(user_id)
    if not user_dir.exists():
        return []
    return sorted(user_dir.glob("*.html"), reverse=True)[:MAX_REPORTS_SHOWN]


@start_router.callback_query(F.data == "reports:list")
async def cb_reports_list(callback: CallbackQuery, lang: str) -> None:
    reports = _user_reports(callback.from_user.id)
    if not reports:
        await callback.answer(get_text(lang, "no_reports_yet"), show_alert=True)
        return
    await callback.message.edit_text(
        get_text(lang, "your_reports"), reply_markup=get_reports_list_keyboard(reports, lang)
    )
    await callback.answer()


@start_router.callback_query(F.data.startswith("reports:send:"))
async def cb_reports_send(callback: CallbackQuery, lang: str) -> None:
    reports = _user_reports(callback.from_user.id)
    index = int(callback.data.removeprefix("reports:send:"))
    if index >= len(reports):
        await callback.answer(get_text(lang, "file_no_longer_exists"), show_alert=True)
        return
    await callback.message.answer_document(FSInputFile(reports[index]))
    await callback.answer()
```

- [ ] **Step 2: Update `tests/test_start_reports.py` if needed**

Run: `python -m pytest tests/test_start_reports.py -v`
Expected: passes unchanged — this test file only exercises `_user_reports`/`REPORTS_DIR`/`MAX_REPORTS_SHOWN`, none of which touch `lang`. No edit needed.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add handlers/start.py
git commit -m "feat: localize handlers/start.py"
```

---

### Task 11: Localize `handlers/search.py`

**Files:**
- Modify: `handlers/search.py`
- Modify: `tests/test_search_handler.py`

**Interfaces:**
- Consumes: `locales.get_text` (Task 5), `report.render.render_report` with its new `lang` parameter (Task 13 — implemented in this task's code, but `report/render.py` itself isn't rewritten until Task 13; see the note in Step 1).
- Produces: `on_query` and `cb_search_new` both gain a `lang: str` parameter.

**Note on task ordering:** this task's `handlers/search.py` code already calls `render_report(..., lang=lang)`. `report/render.py` doesn't accept that parameter yet until Task 13. Do Task 13 immediately after this one (before running `handlers/search.py`'s tests against real rendering) — or, if running strictly in order, expect `test_search_handler.py`'s two tests to still pass in this task because they monkeypatch `run_tools_for_query` to raise/return before `render_report` is ever reached, and they never call `render_report` for real. Task 13 must still land before end-to-end manual testing.

- [ ] **Step 1: Rewrite `handlers/search.py`**

```python
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import get_setting
from keyboards.inline import get_main_menu_keyboard
from locales import get_text
from osint.detect import detect_query_type
from osint.orchestrator import run_tools_for_query
from report.render import render_report

logger = logging.getLogger(__name__)

search_router = Router(name="search")

REPORTS_DIR = Path("reports")

# In-process guard against a user firing a second search while their first
# one is still running. Single-process bot, so a plain in-memory set is
# sufficient; it does not need to survive a restart.
active_requests: set[int] = set()


class SearchStates(StatesGroup):
    waiting_for_query = State()


@search_router.callback_query(F.data == "search:new")
async def cb_search_new(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    if callback.from_user.id in active_requests:
        await callback.answer(get_text(lang, "search_in_progress"), show_alert=True)
        return
    await state.set_state(SearchStates.waiting_for_query)
    await callback.message.edit_text(get_text(lang, "prompt_query"))
    await callback.answer()


@search_router.message(SearchStates.waiting_for_query)
async def on_query(
    message: Message, conn, admin_id: int, blackbird_dir: Path, state: FSMContext, lang: str
) -> None:
    user_id = message.from_user.id
    if user_id in active_requests:
        await message.answer(get_text(lang, "search_in_progress"))
        return

    if not message.text:
        await message.answer(get_text(lang, "please_send_text"))
        return

    query = message.text.strip()
    query_type = detect_query_type(query)
    if query_type is None:
        await message.answer(get_text(lang, "query_not_recognized"))
        return

    active_requests.add(user_id)
    status_message = await message.answer(get_text(lang, "search_running"))
    try:
        try:
            ghunt_enabled = (await get_setting(conn, "ghunt_enabled")) == "true"
            results = await run_tools_for_query(
                query, query_type, blackbird_dir=blackbird_dir, ghunt_enabled=ghunt_enabled
            )
            report_path = render_report(
                query, query_type, results, reports_dir=REPORTS_DIR / str(user_id), lang=lang
            )
            await status_message.edit_text(get_text(lang, "search_done"))
            await message.answer_document(FSInputFile(report_path))
        except Exception:
            logger.exception("Search failed for user_id=%s query=%r", user_id, query)
            await status_message.edit_text(get_text(lang, "search_error"))
    finally:
        active_requests.discard(user_id)
        await state.clear()
        is_admin = user_id == admin_id
        await message.answer(
            get_text(lang, "choose_action"), reply_markup=get_main_menu_keyboard(is_admin, lang)
        )
```

- [ ] **Step 2: Update `tests/test_search_handler.py`**

Add `lang="en"` to both `search.on_query(...)` calls:

```python
        await search.on_query(
            message, conn=conn, admin_id=1, blackbird_dir=Path("."), state=state, lang="en"
        )
```

(Applies to both `test_on_query_with_non_text_message_does_not_crash` and
`test_on_query_reports_failure_on_status_message_and_still_cleans_up`.)

Also update the first test's assertion text (it currently asserts the old
hardcoded Ukrainian string):

```python
        message.answer.assert_awaited_once_with(
            "Please send a text message."
        )
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_search_handler.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add handlers/search.py tests/test_search_handler.py
git commit -m "feat: localize handlers/search.py"
```

---

### Task 12: Localize `handlers/admin.py`

**Files:**
- Modify: `handlers/admin.py`

**Interfaces:**
- Consumes: `locales.get_text` (Task 5), the now-`lang`-aware `keyboards.inline` factories (Task 8).
- Produces: every handler in this router gains a `lang: str` parameter. (No existing test file covers `handlers/admin.py` directly — none is added here, matching the project's current test coverage; the full suite plus a manual smoke test in Task 17 cover it.)

- [ ] **Step 1: Rewrite `handlers/admin.py`**

```python
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
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (no test file exercises `handlers/admin.py` directly today, so this is a regression check on everything else).

- [ ] **Step 3: Commit**

```bash
git add handlers/admin.py
git commit -m "feat: localize handlers/admin.py"
```

---

### Task 13: Localize the HTML report

**Files:**
- Modify: `report/render.py`
- Modify: `report/template.html.j2`
- Modify: `tests/test_render.py`

**Interfaces:**
- Consumes: `locales.get_text` (Task 5).
- Produces: `render_report(query, query_type, results, reports_dir, lang)` — `lang` is now a required parameter; the generated HTML reflects it.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_render.py` with:

```python
from pathlib import Path

from osint.types import ToolResult
from report.render import render_report


def test_render_report_creates_html_file(tmp_path):
    results = [
        ToolResult(
            tool="blackbird",
            status="ok",
            items=[{"label": "GitHub", "value": "https://github.com/mrmozozavr"}],
        ),
        ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено"),
    ]

    out_path = render_report("mrmozozavr", "username", results, reports_dir=tmp_path, lang="uk")

    assert out_path.exists()
    assert out_path.suffix == ".html"
    content = out_path.read_text(encoding="utf-8")
    assert "mrmozozavr" in content
    assert "github.com/mrmozozavr" in content
    assert "НЕДОСТУПНО" in content
    assert "Файл результатів не знайдено" in content


def test_render_report_empty_items_shows_not_found_message(tmp_path):
    results = [ToolResult(tool="holehe", status="ok", items=[])]
    out_path = render_report("user@example.com", "email", results, reports_dir=tmp_path, lang="uk")
    content = out_path.read_text(encoding="utf-8")
    assert "Нічого не знайдено" in content


def test_render_report_escapes_untrusted_tool_output(tmp_path):
    payload = "<script>alert(1)</script>"
    results = [
        ToolResult(
            tool="holehe",
            status="ok",
            items=[{"label": "email", "value": payload}],
        ),
    ]

    out_path = render_report(payload, "username", results, reports_dir=tmp_path, lang="uk")

    content = out_path.read_text(encoding="utf-8")
    assert payload not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


def test_render_report_respects_language(tmp_path):
    results = [ToolResult(tool="holehe", status="ok", items=[])]
    out_path_en = render_report(
        "user@example.com", "email", results, reports_dir=tmp_path, lang="en"
    )
    content_en = out_path_en.read_text(encoding="utf-8")
    assert "Nothing found." in content_en
    assert "OSINT Report: user@example.com" in content_en


def test_render_report_phone_tool_name_is_localized(tmp_path):
    results = [ToolResult(tool="phone", status="ok", items=[{"label": "Region", "value": "UA"}])]
    out_path = render_report("+380001112233", "phone", results, reports_dir=tmp_path, lang="pl")
    content = out_path.read_text(encoding="utf-8")
    assert "Numer telefonu" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_render.py -v`
Expected: `TypeError: render_report() missing 1 required positional argument: 'lang'`.

- [ ] **Step 3: Rewrite `report/render.py`**

```python
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from locales import get_text
from osint.types import ToolResult

TEMPLATE_DIR = Path(__file__).parent

# Proper nouns / brand names - identical across every supported language.
STATIC_TOOL_NAMES = {
    "blackbird": "Blackbird",
    "maigret": "Maigret",
    "sherlock": "Sherlock",
    "holehe": "Holehe",
    "ghunt": "GHunt",
}

QUERY_TYPE_LABEL_KEYS = {
    "email": "query_type_email",
    "phone": "query_type_phone",
    "username": "query_type_username",
}


def _tool_names(lang: str) -> dict[str, str]:
    names = dict(STATIC_TOOL_NAMES)
    names["phone"] = get_text(lang, "tool_phone")
    return names


def render_report(
    query: str, query_type: str, results: list[ToolResult], reports_dir: Path, lang: str
) -> Path:
    # Unconditional autoescape: select_autoescape() decides by filename suffix,
    # and this module's template is named "template.html.j2" (suffix ".j2"),
    # which select_autoescape would NOT recognize as HTML - silently disabling
    # escaping of untrusted OSINT tool output. This module only ever renders
    # this one (always-HTML) template, so autoescape=True is always correct.
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("template.html.j2")
    html = template.render(
        lang=lang,
        report_title=get_text(lang, "report_title", query=query),
        query_type_label=get_text(lang, QUERY_TYPE_LABEL_KEYS[query_type]),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        results=results,
        tool_names=_tool_names(lang),
        status_ok_label=get_text(lang, "report_status_ok"),
        status_unavailable_label=get_text(lang, "report_status_unavailable"),
        nothing_found_label=get_text(lang, "report_nothing_found"),
        tool_unavailable_label=get_text(lang, "report_tool_unavailable"),
        footer_label=get_text(lang, "report_footer"),
    )

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_query = "".join(c if c.isalnum() else "_" for c in query)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"{timestamp}_{safe_query}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Rewrite `report/template.html.j2`**

```jinja2
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ report_title }}</title>
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
  <h1 class="text-3xl font-medium tracking-tight mb-2 text-white">{{ report_title }}</h1>
  <p class="text-xs text-[#a8998f] mb-8 tracking-widest font-light">
    {{ query_type_label|upper }} • {{ generated_at }}
  </p>

  {% for result in results %}
  <div class="tactical-card p-5 rounded-none mb-6">
    <div class="flex items-center justify-between mb-4">
      <span class="text-[10px] text-[#a8998f] tracking-wider font-semibold">
        {{ tool_names.get(result.tool, result.tool) }}
      </span>
      {% if result.status == "ok" %}
        <span class="text-[10px] status-ok">&#9679; {{ status_ok_label }}</span>
      {% else %}
        <span class="text-[10px] status-bad">&#9679; {{ status_unavailable_label }}</span>
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
        <p class="text-[#8c7e75] text-sm">{{ nothing_found_label }}</p>
      {% endif %}
    {% else %}
      <p class="text-[#d88a8a] text-sm">{{ result.error or tool_unavailable_label }}</p>
    {% endif %}
  </div>
  {% endfor %}

  <footer class="w-full flex flex-col items-center mt-12">
    <p class="text-[9px] text-[#4d443f] tracking-widest pt-2">{{ footer_label }}</p>
  </footer>
</main>
</body>
</html>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_render.py -v`
Expected: 6 passed.

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (this closes out the note left in Task 11 — `handlers/search.py`'s `render_report(..., lang=lang)` call is now valid end-to-end).

- [ ] **Step 7: Commit**

```bash
git add report/render.py report/template.html.j2 tests/test_render.py
git commit -m "feat: localize the generated HTML report"
```

---

### Task 14: `.env.example` cleanup

**Files:**
- Modify: `.env.example`

**Interfaces:** none (static file).

- [ ] **Step 1: Rewrite `.env.example`**

```
# Токен бота від @BotFather (https://t.me/botfather)
BOT_TOKEN=123456789:AAExampleTelegramBotToken
# Числовий Telegram ID адміністратора, від @userinfobot (https://t.me/userinfobot)
ADMIN_ID=123456789
```

(`BLACKBIRD_DIR` is removed — blackbird is now vendored at a fixed path, see Task 2.)

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: drop BLACKBIRD_DIR from .env.example"
```

---

### Task 15: README in English, Ukrainian, Polish

**Files:**
- Modify: `README.md`
- Create: `README.uk.md`
- Create: `README.pl.md`

**Interfaces:** none (static files).

- [ ] **Step 1: Rewrite `README.md` (English, default)**

```markdown
English · [Українська](README.uk.md) · [Polski](README.pl.md)

# Easy OSINT Telegram Bot

A Telegram bot for OSINT lookups by username, email, or phone number, using Blackbird, Maigret, Sherlock, Holehe, and GHunt. English / Ukrainian / Polish — every user picks their own language from the bot's menu.

## Requirements

- **Python 3.11 or later**

That's it. Blackbird is vendored directly in this repo (no separate clone), and every other dependency is installed automatically on first run.

## Running the bot

```bash
python main.py
```

The first run will:

1. Install any missing Python dependencies (`pip install -r requirements.txt`).
2. Ask for your `BOT_TOKEN` (from [@BotFather](https://t.me/botfather)) and `ADMIN_ID` (your numeric Telegram ID, from [@userinfobot](https://t.me/userinfobot)) if `.env` doesn't exist yet, and write it.
3. Install GHunt via `pipx` if it isn't already installed.

Every later run skips whatever is already done — `python main.py` is always the only command you need.

`ghunt login` is the one step that stays manual no matter what — it needs a one-time browser-extension flow. Run it once if you want the GHunt (email → Google account recon) tool enabled; toggle it on afterwards in the bot's settings menu.

## First use

1. Open Telegram and message your bot.
2. Send `/start`.
3. **As the administrator** (the user ID you set as `ADMIN_ID`): you have full access immediately. Add other users via "⚙️ Settings" → "👥 Users" → "➕ Add", or switch to "🔓 Mode: Open" to let anyone use it without explicit approval.
4. Pick your language any time via the "🌐 <language>" button on the main menu — it's saved per Telegram user.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

## What `python main.py` does under the hood

See `core/bootstrap.py` — it's a short, readable file. In short: check for missing pip packages and install them, check for `.env` and prompt for it if missing, check for GHunt and install it via pipx if missing. Every step is idempotent (safe to run again).

## License

Blackbird (vendored in `blackbird/`) is licensed under GPLv3 — see `blackbird/LICENSE`. The rest of this project is licensed separately (see `LICENSE` at the repo root, if present) — that license does not apply to `blackbird/`.
```

- [ ] **Step 2: Create `README.uk.md` (Ukrainian)**

```markdown
[English](README.md) · Українська · [Polski](README.pl.md)

# OSINT Telegram-бот

Telegram-бот для OSINT-пошуку за юзернеймом, email чи номером телефону, з використанням Blackbird, Maigret, Sherlock, Holehe та GHunt. Англійська / українська / польська — кожен користувач обирає свою мову в меню бота.

## Вимоги

- **Python 3.11 або новіший**

Це все. Blackbird вендорений прямо в цьому репозиторії (без окремого клонування), а решта залежностей встановлюється автоматично при першому запуску.

## Запуск бота

```bash
python main.py
```

Перший запуск сам:

1. Встановить відсутні Python-залежності (`pip install -r requirements.txt`).
2. Спитає `BOT_TOKEN` (від [@BotFather](https://t.me/botfather)) і `ADMIN_ID` (твій числовий Telegram ID, від [@userinfobot](https://t.me/userinfobot)), якщо `.env` ще нема, і запише його.
3. Встановить GHunt через `pipx`, якщо його ще нема.

Кожен наступний запуск пропускає вже зроблене — `python main.py` завжди єдина потрібна команда.

`ghunt login` — єдиний крок, що лишається ручним у будь-якому разі — потребує одноразового браузерного розширення. Виконай його раз, якщо хочеш увімкнути GHunt (email → розвідка по Google-акаунту); увімкни його потім у меню налаштувань бота.

## Перший запуск

1. Відкрий Telegram і напиши своєму боту.
2. Надішли `/start`.
3. **Як адміністратор** (ID, який ти вказав як `ADMIN_ID`): у тебе одразу повний доступ. Додавай інших через "⚙️ Налаштування" → "👥 Користувачі" → "➕ Додати", або перемкни на "🔓 Режим: Відкритий", щоб дозволити всім без підтвердження.
4. Обери мову будь-коли кнопкою "🌐 <мова>" в головному меню — вона зберігається окремо для кожного користувача Telegram.

## Запуск тестів

```bash
pip install -r requirements-dev.txt
pytest
```

## Що робить `python main.py` під капотом

Дивись `core/bootstrap.py` — короткий, читабельний файл. Коротко: перевіряє відсутні pip-пакети й ставить їх, перевіряє `.env` і питає його, якщо нема, перевіряє GHunt і ставить через pipx, якщо нема. Кожен крок ідемпотентний (безпечно запускати повторно).

## Ліцензія

Blackbird (вендорений у `blackbird/`) під ліцензією GPLv3 — див. `blackbird/LICENSE`. Решта проєкту ліцензована окремо (див. `LICENSE` у корені репозиторію, якщо є) — та ліцензія не поширюється на `blackbird/`.
```

- [ ] **Step 3: Create `README.pl.md` (Polish)**

```markdown
[English](README.md) · [Українська](README.uk.md) · Polski

# Bot OSINT na Telegramie

Bot na Telegramie do wyszukiwań OSINT po nazwie użytkownika, e-mailu lub numerze telefonu, z użyciem Blackbird, Maigret, Sherlock, Holehe i GHunt. Angielski / ukraiński / polski — każdy użytkownik wybiera własny język w menu bota.

## Wymagania

- **Python 3.11 lub nowszy**

To wszystko. Blackbird jest osadzony bezpośrednio w tym repozytorium (bez osobnego klonowania), a każda inna zależność instaluje się automatycznie przy pierwszym uruchomieniu.

## Uruchomienie bota

```bash
python main.py
```

Pierwsze uruchomienie samo:

1. Zainstaluje brakujące zależności Pythona (`pip install -r requirements.txt`).
2. Zapyta o `BOT_TOKEN` (od [@BotFather](https://t.me/botfather)) i `ADMIN_ID` (twój numeryczny Telegram ID, od [@userinfobot](https://t.me/userinfobot)), jeśli `.env` jeszcze nie istnieje, i zapisze go.
3. Zainstaluje GHunt przez `pipx`, jeśli nie jest jeszcze zainstalowany.

Każde kolejne uruchomienie pomija to, co już zrobione — `python main.py` to zawsze jedyna potrzebna komenda.

`ghunt login` to jedyny krok, który zawsze pozostaje ręczny — wymaga jednorazowego przepływu przez rozszerzenie przeglądarki. Wykonaj go raz, jeśli chcesz włączyć GHunt (e-mail → rozpoznanie konta Google); włącz go potem w menu ustawień bota.

## Pierwsze użycie

1. Otwórz Telegram i napisz do swojego bota.
2. Wyślij `/start`.
3. **Jako administrator** (ID, które ustawiłeś jako `ADMIN_ID`): masz od razu pełny dostęp. Dodawaj innych przez "⚙️ Ustawienia" → "👥 Użytkownicy" → "➕ Dodaj", albo przełącz na "🔓 Tryb: Otwarty", aby pozwolić każdemu bez zatwierdzania.
4. Wybierz język w dowolnym momencie przyciskiem "🌐 <język>" w menu głównym — jest zapisywany osobno dla każdego użytkownika Telegramu.

## Uruchamianie testów

```bash
pip install -r requirements-dev.txt
pytest
```

## Co robi `python main.py` pod maską

Zobacz `core/bootstrap.py` — krótki, czytelny plik. W skrócie: sprawdza brakujące pakiety pip i je instaluje, sprawdza `.env` i pyta o niego, jeśli go nie ma, sprawdza GHunt i instaluje go przez pipx, jeśli go nie ma. Każdy krok jest idempotentny (bezpiecznie uruchomić ponownie).

## Licencja

Blackbird (osadzony w `blackbird/`) jest na licencji GPLv3 — zobacz `blackbird/LICENSE`. Reszta projektu jest licencjonowana osobno (zobacz `LICENSE` w katalogu głównym repozytorium, jeśli istnieje) — ta licencja nie obejmuje `blackbird/`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md README.uk.md README.pl.md
git commit -m "docs: rewrite README for zero-friction setup, add uk/pl translations"
```

---

### Task 16: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update §1 (header)**

Append one sentence to the existing header paragraph:

```
Мова коду й коментарів — англійська; мова user-facing текстів бота (повідомлення, кнопки, логи для читання людиною) — українська. Не змішувати ці дві мови в одному місці: коментарі не переводити на українську, user-facing рядки не писати англійською.
```

becomes:

```
Мова коду й коментарів — англійська; мова user-facing текстів бота (повідомлення, кнопки, логи для читання людиною) — українська. Не змішувати ці дві мови в одному місці: коментарі не переводити на українську, user-facing рядки не писати англійською. User-facing текст бота (повідомлення, кнопки, згенерований звіт) тепер багатомовний через `locales.py::get_text(lang, key)` — див. §5 — а не захардкожений українською; сам код/коментарі це не стосується.
```

- [ ] **Step 2: Update §2 stack table**

In the stack table, add a row:

```
| i18n | `locales.py` — flat `TEXTS[lang][key]` dict + `get_text()`, per-user choice stored in DB (en/uk/pl) |
```

- [ ] **Step 3: Update §2 structure tree**

Replace the tree in §2 with (adds `core/bootstrap.py`, `locales.py`, `handlers/language.py`, drops `scripts/`):

```
main.py                    # єдина точка входу: core.bootstrap.ensure_ready() потім asyncio.run(main())
core/
├── config.py               # Config(dataclass) + load_config() з валідацією .env
├── bootstrap.py             # ensure_ready() — авто-install залежностей, .env-промпт, GHunt через pipx
└── loader.py                 # create_bot()/create_dispatcher() — Bot із ThreadedResolver, Dispatcher
locales.py                  # TEXTS[lang][key] (en/uk/pl) + get_text(lang, key, **kwargs)
handlers/
├── admin.py                 # admin_router — керування whitelist/access_mode/GHunt-тумблером
├── search.py                 # search_router — FSM пошуку, запуск інструментів, рендер звіту
├── start.py                   # start_router — /start, головне меню, список звітів користувача
└── language.py                 # language_router — вибір мови (кожен користувач окремо)
keyboards/
└── inline.py                  # get_<what>_keyboard(..., lang) фабрики інлайн-клавіатур
middlewares/
└── auth.py                    # AuthMiddleware — перевірка доступу + завантаження lang на кожному запиті
database.py                    # ОДИН файл-модуль: aiosqlite CRUD (users, settings, user_language)
osint/
├── detect.py                   # detect_query_type(): email | phone | username | None
├── orchestrator.py             # run_tools_for_query() — паралельний запуск інструментів
├── types.py                     # ToolResult dataclass
└── runners/                     # один runner на інструмент, кожен повертає ToolResult
    ├── blackbird.py, maigret.py, sherlock.py   # username
    ├── holehe.py, ghunt.py                      # email
    └── phone.py                                  # телефон
report/
├── render.py                   # render_report(..., lang) — Jinja2 → HTML файл у reports/<user_id>/
└── template.html.j2
blackbird/                       # ВЕНДОРЕНИЙ сторонній інструмент (GPLv3, LICENSE збережено), не клонується
tests/                           # дзеркалить структуру кореня (test_<module>.py)
```

- [ ] **Step 4: Update §3 (config table)**

Replace the `.env` table (drop `BLACKBIRD_DIR` row):

```
| Змінна | Обов'язкова? | Призначення |
|---|---|---|
| `BOT_TOKEN` | так | Токен бота від @BotFather |
| `ADMIN_ID` | так | Telegram ID адміністратора — повний доступ завжди, і бачить меню налаштувань |
```

Add a sentence after the table:

```
`BLACKBIRD_DIR` більше не існує — blackbird вендорений прямо в репо за фіксованим шляхом (`core/config.py::BLACKBIRD_DIR`), а не клонується окремо. `core/bootstrap.py::ensure_ready()` питає `BOT_TOKEN`/`ADMIN_ID` інтерактивно й пише `.env` сам, якщо його нема — не треба налаштовувати вручну.
```

- [ ] **Step 5: Update §4 (module map)**

Add two rows to the module-map table:

```
| `core/bootstrap.py` | `ensure_ready()` — ідемпотентний запуск на кожному старті: встановлює відсутні pip-залежності, питає `.env` якщо нема, ставить GHunt через pipx якщо нема, повертає `Config` |
| `locales.py` | `TEXTS[lang][key]` (en/uk/pl) + `get_text(lang, key, **kwargs)` з fallback на англійську, потім на сирий ключ |
| `handlers/language.py` | `language_router` — кнопка "🌐 <мова>" в головному меню, `set_user_language` в `database.py` |
```

- [ ] **Step 6: Update §6 (pitfalls) — rewrite the DNS-resolver entry, add bootstrap idempotency entry**

Replace the existing "DNS-резолвер aiohttp на Windows" bullet's second sub-point (about `scripts/setup.py::patch_blackbird_dns_resolver_bug()`) with:

```
  - Вендорений blackbird (`blackbird/src/modules/core/{username,email}.py`, `aiohttp.ClientSession()`) — пропатчено НАЗАВЖДИ прямо у вендорених вихідниках (форсує `ThreadedResolver`), оскільки більше нема свіжого клону, який патчити при кожному сетапі. Якщо колись знову оновлюватимеш blackbird вручну з апстріму — патч треба накласти повторно.
```

Add a new bullet at the end of §6:

```
- **`core/bootstrap.py::ensure_ready()` мусить лишатись безпечним для повторного виклику.** Він запускається на КОЖНОМУ старті `main.py`, не лише при першому. Будь-яка нова перевірка тут має спершу спитати "чи вже зроблено?" і вийти рано, а не сліпо перевстановлювати/перезаписувати щоразу.
```

- [ ] **Step 7: Update §7 (agent rules)**

Add one bullet:

```
- Новий user-facing рядок у боті чи звіті — завжди через `locales.py::TEXTS`/`get_text()`, з однаковим ключем у всіх трьох мовах (en/uk/pl). Ніколи не хардкодь текст напряму в хендлері/клавіатурі/шаблоні.
```

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for bootstrap, vendored blackbird, and i18n"
```

---

### Task 17: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass, zero failures.

- [ ] **Step 2: Confirm no stale references remain**

Run: `grep -rn "BLACKBIRD_DIR\|scripts/setup.py\|scripts\.setup" --include="*.py" --include="*.md" .`
Expected: matches only inside `docs/superpowers/` (historical spec/plan files, which describe past/point-in-time state and are not live code) — nothing in `README*.md`, `CLAUDE.md`, or any `.py` file under `core/`, `handlers/`, `keyboards/`, `middlewares/`, `osint/`, `report/`, `database.py`, `main.py`, `locales.py`, or `tests/`.

- [ ] **Step 3: Sanity-import the whole app**

Run: `python -c "import main; print('main.py imports OK')"`
Expected: `main.py imports OK`.

- [ ] **Step 4: Confirm blackbird is tracked and its license is intact**

Run: `git ls-files blackbird/LICENSE blackbird/blackbird.py && test -f blackbird/LICENSE && head -3 blackbird/LICENSE`
Expected: both paths listed as tracked, and the license header starts with `GNU GENERAL PUBLIC LICENSE`.

- [ ] **Step 5: Manual smoke test (cannot be automated — needs a real Telegram client)**

Ask the user to:
1. Temporarily rename their existing `.env` (e.g. `.env` → `.env.bak`) in a scratch copy of the repo, or confirm they're fine testing bootstrap prompts on the real one.
2. Run `python main.py` and confirm it prompts for `BOT_TOKEN`/`ADMIN_ID` (or skips straight to polling if `.env` already exists) with no other manual step.
3. In Telegram, send `/start`, confirm the main menu shows in English by default.
4. Tap "🌐 English", switch to Ukrainian, confirm the menu re-renders in Ukrainian and stays that way on the next `/start`.
5. Run a search (any query type) and confirm the downloaded HTML report is in the language just selected.
6. Switch to Polish and repeat step 5 to confirm the report follows the language too.

Report back the outcome before considering this plan complete.
