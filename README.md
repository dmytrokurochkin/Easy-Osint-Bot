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
