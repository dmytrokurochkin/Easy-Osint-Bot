"""One-shot installer for the OSINT Telegram bot.

Installs everything the bot needs to run (Python deps, blackbird, GHunt)
without Docker, and interactively fills in .env. Safe to re-run: it skips
steps that are already done.

Usage: python scripts/setup.py
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows consoles sometimes default to a legacy codepage (e.g. cp1252) that
# can't encode Ukrainian text; force UTF-8 output so this script's messages
# never crash it regardless of the terminal's configuration.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, "encoding", "").lower() != "utf-8":
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BLACKBIRD_DIR = PROJECT_ROOT / "blackbird"
BLACKBIRD_REPO_URL = "https://github.com/p1ngul1n0/blackbird"
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"


def run(cmd: list[str], **kwargs) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT, **kwargs)


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def install_python_requirements() -> None:
    step("Встановлюю Python-залежності бота")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"])


def strip_version_pins(requirements_path: Path) -> Path:
    """Write a copy of a requirements file with exact version pins removed.

    Some tools (blackbird included) pin exact old versions that may have no
    prebuilt wheel for a very new Python — pip then tries to compile them
    from C source, which needs a full compiler toolchain most machines don't
    have. Letting pip pick its own (wheel-having) version is far more likely
    to just work.
    """
    unpinned_lines = []
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = re.split(r"[<>=!~;]", stripped, maxsplit=1)[0].strip()
        if name:
            unpinned_lines.append(name)

    unpinned_path = requirements_path.with_name(requirements_path.stem + "_unpinned.txt")
    unpinned_path.write_text("\n".join(unpinned_lines) + "\n", encoding="utf-8")
    return unpinned_path


def pip_install_requirements(requirements_path: Path) -> None:
    try:
        run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)])
    except subprocess.CalledProcessError:
        print(
            f"\n{requirements_path.name}: встановлення з точними версіями не вдалося "
            "(типово через відсутність готового wheel під твою версію Python).\n"
            "Пробую ще раз без фіксованих версій — pip сам підбере сумісні..."
        )
        unpinned_path = strip_version_pins(requirements_path)
        run([sys.executable, "-m", "pip", "install", "-r", str(unpinned_path)])


def patch_blackbird_windows_console_bug() -> None:
    """Work around a blackbird/rich crash on Windows.

    blackbird prints an ASCII-art banner on every run via `Console()`. On
    Windows, when stdout has no real console attached (which is exactly how
    we run it — piped, from this bot), rich's "legacy Windows console"
    detection misfires and crashes with a UnicodeEncodeError on the banner's
    block-drawing characters before blackbird does anything else. Passing
    `legacy_windows=False` makes rich use its normal (working) write path.
    Idempotent — safe to call every run.
    """
    if sys.platform != "win32":
        return
    blackbird_py = BLACKBIRD_DIR / "blackbird.py"
    if not blackbird_py.exists():
        return
    original = "config.console = Console()"
    patched = "config.console = Console(legacy_windows=False)"
    content = blackbird_py.read_text(encoding="utf-8")
    if original in content:
        blackbird_py.write_text(content.replace(original, patched), encoding="utf-8")
        print("Застосовано патч сумісності з Windows-консоллю для blackbird.")


def patch_blackbird_dns_resolver_bug() -> None:
    """Work around aiodns failing to contact DNS servers on some setups.

    blackbird opens `aiohttp.ClientSession()` with no resolver override, so
    aiohttp defaults to the aiodns-backed AsyncResolver whenever the aiodns
    package is importable. On machines where pycares can't read the system
    DNS config (seen on Windows, e.g. certain VPN/adapter setups), every
    single HTTP request then fails with "Could not contact DNS servers" —
    blackbird exits cleanly with zero accounts found instead of crashing,
    which looks like "nothing found" rather than "broken". Plain
    `socket.getaddrinfo` (what requests/urllib use, and what the bot's other
    tools rely on) resolves fine in that situation, so forcing aiohttp onto
    the socket-based ThreadedResolver fixes it without needing aiodns at
    all. Idempotent — safe to call every run.
    """
    for relative_path in ("src/modules/core/username.py", "src/modules/core/email.py"):
        target = BLACKBIRD_DIR / relative_path
        if not target.exists():
            continue
        original = "aiohttp.ClientSession()"
        patched = (
            "aiohttp.ClientSession(connector=aiohttp.TCPConnector("
            "resolver=aiohttp.ThreadedResolver()))"
        )
        content = target.read_text(encoding="utf-8")
        if original in content:
            target.write_text(content.replace(original, patched), encoding="utf-8")
            print(f"Застосовано патч DNS-резолвера для {relative_path}.")


def install_blackbird() -> None:
    step("blackbird (username OSINT)")
    if BLACKBIRD_DIR.exists():
        print(f"Вже є: {BLACKBIRD_DIR} — пропускаю git clone.")
    else:
        if shutil.which("git") is None:
            print("git не знайдено в PATH. Встанови git і запусти скрипт ще раз.")
            sys.exit(1)
        run(["git", "clone", BLACKBIRD_REPO_URL, str(BLACKBIRD_DIR)])

    patch_blackbird_windows_console_bug()
    patch_blackbird_dns_resolver_bug()

    blackbird_requirements = BLACKBIRD_DIR / "requirements.txt"
    if blackbird_requirements.exists():
        pip_install_requirements(blackbird_requirements)


def ensure_pipx() -> bool:
    if shutil.which("pipx") is not None:
        return True
    print("pipx не знайдено — встановлюю через pip...")
    try:
        run([sys.executable, "-m", "pip", "install", "--user", "pipx"])
        run([sys.executable, "-m", "pipx", "ensurepath"])
    except subprocess.CalledProcessError:
        print("Не вдалося автоматично встановити pipx. Постав вручну: pip install --user pipx")
        return False
    return True


def install_ghunt() -> None:
    step("GHunt (опційно, email → Google recon)")
    if not ensure_pipx():
        print("Пропускаю встановлення GHunt — постав вручну пізніше: pipx install ghunt")
        return
    # pipx's own PATH entry may not be visible yet in this process (ensurepath
    # only takes effect in new shells), so always invoke it via `python -m pipx`.
    pipx_cmd = [sys.executable, "-m", "pipx"]
    try:
        run(pipx_cmd + ["install", "ghunt"])
    except subprocess.CalledProcessError:
        # pipx exits non-zero if the package is already installed — treat as fine.
        print("GHunt вже встановлений або встановлення пропущено (перевір: pipx list).")
    print(
        "GHunt встановлено. Логін лишається ручним — це неминуче:\n"
        "  ghunt login\n"
        "(один раз, через браузерне розширення GHunt Companion)."
    )


def write_env_file() -> None:
    step("Налаштування .env")
    if ENV_PATH.exists():
        print(f"{ENV_PATH} вже існує — не чіпаю. Онови BLACKBIRD_DIR вручну, якщо треба:")
        print(f"  BLACKBIRD_DIR={BLACKBIRD_DIR}")
        return

    print("Зараз потрібні два значення з Telegram (взяти можна тільки вручну):")
    print("  BOT_TOKEN — від @BotFather (https://t.me/botfather)")
    print("  ADMIN_ID  — твій числовий ID від @userinfobot (https://t.me/userinfobot)")
    bot_token = input("BOT_TOKEN: ").strip()
    admin_id = input("ADMIN_ID: ").strip()

    ENV_PATH.write_text(
        f"BOT_TOKEN={bot_token}\n"
        f"ADMIN_ID={admin_id}\n"
        f"BLACKBIRD_DIR={BLACKBIRD_DIR}\n",
        encoding="utf-8",
    )
    print(f"Записано {ENV_PATH}")


def main() -> None:
    install_python_requirements()
    install_blackbird()
    install_ghunt()
    write_env_file()

    step("Готово")
    print("Запуск бота:")
    print("  python main.py")
    print("\nЯкщо ще не логінив GHunt і хочеш ним користуватись:")
    print("  ghunt login")


if __name__ == "__main__":
    main()
