import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

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
    print(f"Installing missing dependencies: {', '.join(missing)}...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)],
        check=True,
    )


def _ensure_env_file() -> None:
    if ENV_PATH.exists():
        return
    print("No .env file found. Two values from Telegram are needed:")
    bot_token = input("BOT_TOKEN (from @BotFather, https://t.me/botfather): ").strip()
    admin_id = input("ADMIN_ID (your numeric Telegram ID from @userinfobot, https://t.me/userinfobot): ").strip()
    ENV_PATH.write_text(f"BOT_TOKEN={bot_token}\nADMIN_ID={admin_id}\n", encoding="utf-8")
    print(f"Wrote {ENV_PATH}")


def _ensure_ghunt() -> None:
    if shutil.which("ghunt") is not None:
        return
    print("GHunt not found — installing via pipx...")
    if shutil.which("pipx") is None:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pipx"], check=True)
            subprocess.run([sys.executable, "-m", "pipx", "ensurepath"], check=True)
        except subprocess.CalledProcessError:
            print("Could not install pipx automatically. Install it manually: pip install --user pipx")
            return
    try:
        subprocess.run([sys.executable, "-m", "pipx", "install", "ghunt"], check=True)
    except subprocess.CalledProcessError:
        # A failed install here is NOT the same as "already installed" - the
        # most common cause on a very new Python (e.g. 3.14 at the time of
        # writing) is that one of GHunt's dependencies (pillow) has no
        # prebuilt wheel yet and fails compiling from source. GHunt is
        # optional (ghunt_enabled defaults to false), so this must never
        # block the bot from starting - just tell the user honestly.
        print(
            "Could not install GHunt automatically (see the pip/uv output above "
            "for why - often a dependency with no prebuilt wheel for this Python "
            "version yet). GHunt is optional; the bot will run without it. To "
            "install it yourself: pipx install ghunt --python <path to an older "
            "Python, e.g. 3.11 or 3.12>, or check: pipx list"
        )
        return
    print("If this is GHunt's first run, log in manually: ghunt login")


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv()


def ensure_ready() -> Config:
    """Idempotent - safe to call on every startup. Skips whatever is
    already satisfied, so a second/third/nth run is nearly instant."""
    _ensure_dependencies()
    _ensure_env_file()
    _load_env()
    _ensure_ghunt()
    return load_config()
