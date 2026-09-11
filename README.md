# Easy OSINT Telegram Bot

A Telegram bot for performing OSINT operations using Blackbird, Sherlock, and GHunt.

## Prerequisites

- **Python 3.11 or later**
- **git** (to clone blackbird)

`pipx` is bootstrapped automatically by `scripts/setup.py` if missing. No Docker needed.

## Installation

### Quick start (recommended)

One command installs everything (Python deps, blackbird, GHunt) and asks for `BOT_TOKEN`/`ADMIN_ID` interactively:

```bash
python scripts/setup.py
```

Safe to re-run — it skips anything already installed, and never overwrites an existing `.env`.

`ghunt login` is the one step that stays manual no matter what (it needs a one-time browser-extension flow) — the script prints a reminder for it at the end.

### Manual install

If you'd rather do it by hand, or the script fails on your system:

1. **Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Blackbird** (not a pip package — clone and install separately):
   ```bash
   git clone https://github.com/p1ngul1n0/blackbird
   pip install -r blackbird/requirements.txt
   ```

3. **`.env`:** copy `.env.example` to `.env` and fill in:
   - **BOT_TOKEN** — from [@BotFather](https://t.me/botfather)
   - **ADMIN_ID** — your numeric Telegram ID, from [@userinfobot](https://t.me/userinfobot)
   - **BLACKBIRD_DIR** — absolute path to the blackbird clone from step 2

   Example:
   ```
   BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij
   ADMIN_ID=987654321
   BLACKBIRD_DIR=/path/to/blackbird
   ```

4. **Optional: GHunt** (email → Google account recon):
   ```bash
   pipx install ghunt
   ghunt login
   ```
   Follow the GHunt Companion browser extension instructions when prompted. Afterwards, enable it in the bot via the GHunt toggle in the settings menu.

## Running the Bot

Start the bot with:

```bash
python main.py
```

The bot will log its startup and begin polling Telegram for updates. You should see output similar to:

```
INFO:root:...
INFO:aiogram.dispatcher:Dispatcher started polling
```

## First Use

1. Open Telegram and message your bot by finding it through search or using a direct link (e.g., `https://t.me/YourBotUsername`).

2. Send the `/start` command to initialize the bot.

3. **As the bot administrator (the user ID you set as ADMIN_ID):**
   - You have full access to all bot features immediately.
   - To add other users, go to "⚙️ Налаштування" (Settings) → "👥 Користувачі" (Users) → "➕ Додати" (Add).
   - Alternatively, switch the bot to "🔓 Режим: Відкритий" (Open Mode) to allow anyone to use it without explicit approval.

## Running Tests

Execute the test suite to verify the bot components are working correctly:

```bash
pytest
```

All tests should pass before deploying the bot to production.
