# Design: Zero-friction setup, vendored blackbird, 3-language i18n

Date: 2026-09-11
Status: Approved by user, pending implementation plan

## Context

Current state (as of the previous session's restructure to a flat
`main.py`/`core/`/`handlers/`/... layout):

- `blackbird/` is a `.gitignore`d git clone, provisioned by
  `scripts/setup.py::install_blackbird()` (clones from GitHub, patches two
  Windows-specific bugs into the clone: a `rich` console crash and an
  `aiodns` DNS-resolver failure).
- `.env` requires `BOT_TOKEN`, `ADMIN_ID`, `BLACKBIRD_DIR` — the last one
  points at wherever the user cloned blackbird.
- `scripts/setup.py` is a separate one-shot installer the user must run
  manually before `python main.py` works.
- All user-facing bot text (messages, keyboard labels, the HTML report) is
  hardcoded Ukrainian. No language selection exists.
- README exists only in English.

The user tested the bot, everything works except GHunt (expected — GHunt
requires an interactive one-time browser-extension login, which cannot be
automated). They now want three things, confirmed section-by-section:

1. Nothing to install or configure separately — running `python main.py`
   should bootstrap everything itself (deps, blackbird, `.env` keys).
2. Blackbird vendored directly into this repo (no runtime git clone).
3. Full 3-language i18n (English default, Ukrainian, Polish) — every
   user-facing bot string, per-user selectable via a menu button, plus the
   generated HTML report — and a 3-language README.

A licensing concern was raised and resolved during brainstorming: blackbird
is GPLv3. It is vendored as a subdirectory with its own `LICENSE`/attribution
kept intact. The user's own license (to be added later) covers only the
code they authored themselves; it does not and cannot relicense blackbird.

## Goals

- `git clone` this repo, then `python main.py` — no other manual step
  except answering two interactive prompts (`BOT_TOKEN`, `ADMIN_ID`) on
  first run — brings the bot to a fully working state (blackbird included).
- Every user picks their own language (en/uk/pl) via a menu button; it
  persists per Telegram user id and affects every message, keyboard, and
  generated report they see.
- README readable in English (default), Ukrainian, or Polish.

## Non-goals

- Automating GHunt's login (structurally impossible — it's an interactive
  OAuth browser-extension flow).
- A general-purpose i18n framework (gettext/babel/fluent). This project's
  scale calls for the simple `locales.py` + `get_text(lang, key)` pattern
  already used in the user's other bots — see repo-style conventions.
- Auto-detecting language from `message.from_user.language_code`. Rejected
  during brainstorming in favor of an explicit per-user menu choice,
  defaulting everyone to English until they change it.
- Vendoring maigret/holehe/sherlock-project — these are already ordinary
  PyPI packages installed via `requirements.txt`; only blackbird needed a
  separate git clone.

## 1. Bootstrap and vendored blackbird

### Vendoring

- `blackbird/` is un-ignored and committed as regular tracked files.
  Its own `.git/` is removed first (plain vendored source, not a
  submodule — a submodule would still require a separate fetch step,
  which defeats the "nothing to download separately" goal).
  Its own `LICENSE`/`README.md`/`docs/` stay untouched (GPLv3 attribution).
  Its own runtime-generated subdirectories (`logs/`, `results/`,
  `__pycache__/`, `.env`) stay gitignored — only the source is vendored,
  not its output.
- The two Windows compatibility patches (rich console `legacy_windows`,
  aiohttp `ThreadedResolver` for the aiodns DNS bug — see current
  `CLAUDE.md` §6) are applied once, directly to the vendored source, and
  committed as-is. There is no more "patch on every setup run" step,
  because there is no more fresh clone to patch.
- `core/config.py`'s `blackbird_dir` becomes a fixed constant
  (`Path(__file__).resolve().parent.parent / "blackbird"`), not a `.env`
  value. `BLACKBIRD_DIR` is removed from `Config`, `.env`, and
  `.env.example`.

### `core/bootstrap.py` (new)

Runs at the very top of `main.py`, before any heavy import, as a plain
synchronous function `ensure_ready() -> Config`. Idempotent — safe to run
on every startup, skips whatever is already satisfied (mirrors
`scripts/setup.py`'s existing "safe to re-run" behavior, which this
module replaces).

Steps, in order:

1. **Dependencies.** Try importing each top-level package the bot and the
   vendored blackbird need (`aiogram`, `aiosqlite`, `dotenv`, `phonenumbers`,
   `jinja2`, `aiohttp`, `rich`, `chardet`, plus the already-PyPI OSINT
   tools). On any `ImportError`, run
   `pip install -r requirements.txt` via `subprocess`, then re-check.
   `requirements.txt` gains blackbird's own runtime dependencies (merged
   in, deduplicated) so one install covers both.
2. **`.env`.** If missing, or `BOT_TOKEN`/`ADMIN_ID` are unset/blank,
   prompt interactively via `input()` for each (same UX as today's
   `scripts/setup.py::write_env_file`, minus the now-removed
   `BLACKBIRD_DIR` prompt), write `.env`.
3. **GHunt.** If `shutil.which("ghunt")` is `None`, bootstrap pipx (same
   logic as today's `ensure_pipx()`) and run `pipx install ghunt`
   non-interactively. Always print the one unavoidable manual step
   (`ghunt login`) as a reminder if GHunt is installed but a login check
   (`ghunt login --check`, if available) fails — best-effort; never blocks
   startup.
4. Return a loaded `Config` (calls `load_dotenv()` + `core.config.load_config()`
   internally now that `.env` is guaranteed to exist).

`main.py` becomes:

```python
from core.bootstrap import ensure_ready
config = ensure_ready()
# ... existing asyncio.run(main(config)) flow, unchanged otherwise
```

`scripts/setup.py` and the now-empty `scripts/` directory are deleted;
its logic lives in `core/bootstrap.py`. `tests/` gains
`test_bootstrap.py` covering: missing `.env` triggers prompts (mocked
`input`), present `.env` with real values skips prompting, missing import
triggers a (mocked) `pip install` call.

## 2. i18n (English / Ukrainian / Polish)

### `locales.py` (new, root, single module — per repo-style convention)

```python
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en": "English", "uk": "Українська", "pl": "Polski"}

TEXTS: dict[str, dict[str, str]] = {
    "en": {...},
    "uk": {...},
    "pl": {...},
}

def get_text(lang: str, key: str, **kwargs) -> str:
    """Look up TEXTS[lang][key]; fall back to English, then to the raw
    key itself if even English is missing it (never raises — a missing
    translation must never crash a handler). Formats with **kwargs."""
```

Every user-facing string currently hardcoded in `handlers/*.py`,
`keyboards/inline.py`, and `middlewares/auth.py` (the two
`UNAUTHORIZED_*` constants) moves into `TEXTS` under a stable key
(e.g. `"main_menu_prompt"`, `"admin_only"`, `"report_ready"`). Ukrainian
text already in the codebase becomes the `"uk"` entries verbatim (no
retranslation needed there); English and Polish are authored fresh.

### Per-user language storage

New table in `database.py`, independent of the whitelist `users` table
(the admin must have a language preference too, and isn't necessarily a
row in `users`):

```sql
CREATE TABLE IF NOT EXISTS user_language (
    telegram_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'en'
);
```

`get_user_language(conn, telegram_id) -> str` (returns `DEFAULT_LANGUAGE`
if no row), `set_user_language(conn, telegram_id, language) -> None`
(`INSERT ... ON CONFLICT DO UPDATE`, same pattern as `set_setting`).

### Wiring `lang` through the request

`AuthMiddleware` (`middlewares/auth.py`), which already runs as outer
middleware on every event and already loads `conn`/`admin_id`/`user`,
additionally loads `lang = await get_user_language(conn, user.id)` and
injects it into `data["lang"]` right before calling the wrapped handler.
Every handler function gains a `lang: str` parameter (aiogram's DI passes
it automatically, same mechanism as the existing `conn`/`admin_id`
parameters) — no handler manually queries the DB for its own language.

### Keyboards

Every factory in `keyboards/inline.py` gains a `lang: str` parameter;
button labels come from `get_text(lang, ...)` instead of hardcoded
Ukrainian literals. Static `callback_data` values (`"admin:menu"`,
`"search:new"`, etc.) are unchanged — only display text is localized.

### New language picker

`handlers/language.py` (new, `language_router`):

- `get_language_menu_keyboard(current: str)` in `keyboards/inline.py` —
  one button per `SUPPORTED_LANGUAGES` entry, callback_data
  `"lang:set:en"` / `"lang:set:uk"` / `"lang:set:pl"`, checkmark on the
  currently active one.
- `main_menu` (all users, not just admin) gains a "🌐 <language name>"
  button (`callback_data="lang:menu"`) opening the picker.
- `cb_language_menu` shows the picker; `cb_set_language` (matches
  `F.data.startswith("lang:set:")`) calls `set_user_language`, then
  re-renders the main menu using the newly chosen language.
- Registered in `main.py` alongside the other three routers, with
  `AuthMiddleware` attached the same way.

### Report localization

`report/render.py::render_report` gains a `lang: str` parameter (the
language of the user who requested the search, threaded through from
`handlers/search.py`, which already has `lang` via DI). `TOOL_NAMES`
becomes `TOOL_NAMES[lang][tool_key]`; the template context passes
already-resolved strings (`report_title`, `generated_label`,
`footer_text`, per-tool localized labels) instead of raw keys, keeping
`template.html.j2` free of any `get_text` calls — it stays a pure
presentation template.

## 3. README

- `README.md` (English, default/primary) rewritten: drop the "Manual
  install" section's per-tool steps (blackbird clone, separate `pip
  install`) since bootstrap now does all of it; keep a short "what
  bootstrap does under the hood" note for transparency. Run command:
  `python main.py`.
- `README.uk.md`, `README.pl.md` — same structure and content, translated.
- A one-line language-switcher at the top of all three
  (`English · [Українська](README.uk.md) · [Polski](README.pl.md)`,
  adjusted per file).
- `CLAUDE.md` updated: §1 already states English code / Ukrainian
  user-facing text — add a note that user-facing text is now
  multi-language via `locales.py`, not hardcoded Ukrainian. §3 config
  table drops `BLACKBIRD_DIR`. §6 pitfalls: rewrite the DNS-resolver entry
  to reflect blackbird now being pre-patched vendored source rather than
  patched-on-clone; add an entry for `core/bootstrap.py`'s
  idempotency requirement (must stay safe to run on every single startup,
  not just the first).

## Testing

- `tests/test_bootstrap.py` (new) — see §1.
- `tests/test_locales.py` (new) — `get_text` fallback behavior (missing
  key, missing language, formatting kwargs).
- `tests/test_db.py` — extend with `user_language` get/set/default cases.
- `tests/test_middlewares.py` — extend to assert `lang` lands in `data`.
- `tests/test_keyboards.py` — extend for the new `lang` parameter and the
  new language-picker keyboard.
- Existing handler tests (`test_search_handler.py`, `test_start_reports.py`)
  updated for the new `lang` parameter handlers now require.
- `tests/test_render.py` — extend for `lang` parameter / localized
  `TOOL_NAMES`.
- Full `pytest -q` must pass before this is considered done.

## Risks / open questions carried into planning

- Merging blackbird's `requirements.txt` into the root `requirements.txt`
  needs a real dependency-conflict check (both already share `aiohttp`
  transitively via maigret/holehe, versions must be compatible) — a
  planning-time task, not a design decision.
- Polish translations are authored by the agent, not a native speaker —
  acceptable for a personal tool per the user's own framing, but worth
  flagging as machine-quality Polish, not professionally reviewed.
