# Easy OSINT Telegram Bot

A Telegram bot for performing OSINT operations using Blackbird, Sherlock, and GHunt.

## Prerequisites

- **Python 3.11 or later**
- **git** (to clone repositories)
- **pipx** (for installing command-line tools globally)

Ensure these are installed and available in your PATH before proceeding.

## Installation

### 1. Install Python Dependencies

Install the bot's Python dependencies:

```bash
pip install -r requirements.txt
```

### 2. Install and Configure Blackbird

Blackbird is a OSINT tool that must be cloned and installed separately:

```bash
git clone https://github.com/p1ngul1n0/blackbird
pip install -r blackbird/requirements.txt
```

After installation, set the `BLACKBIRD_DIR` environment variable in your `.env` file to the absolute path of the cloned blackbird directory. For example:

```
BLACKBIRD_DIR=/path/to/blackbird
```

### 3. Configure Environment Variables

Copy the example environment file and fill in your configuration:

```bash
cp .env.example .env
```

Edit `.env` and provide the following values:

- **BOT_TOKEN**: Your Telegram bot token. Get this from [@BotFather](https://t.me/botfather) on Telegram.
- **ADMIN_ID**: Your Telegram numeric user ID. You can get this from [@userinfobot](https://t.me/userinfobot) on Telegram.

Example `.env`:

```
BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij
ADMIN_ID=987654321
BLACKBIRD_DIR=/path/to/blackbird
```

### 4. Optional: Install GHunt (Google Intelligence)

GHunt allows gathering information about Google accounts. If you want to use this feature:

```bash
pipx install ghunt
ghunt login
```

Follow the GHunt Companion browser extension instructions when prompted. After completing the login flow, GHunt features will be available in the bot via the GHunt toggle in the settings menu.

## Running the Bot

Start the bot with:

```bash
python -m bot.main
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
