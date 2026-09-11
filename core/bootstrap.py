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
