import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from osint.types import ToolResult

logger = logging.getLogger(__name__)

# maigret checks ~500 sites by default with the (more reliable, but slower)
# threaded DNS resolver — observed taking well over 120s in practice, unlike
# the other tools. Give it more room; this is per-module, not a project-wide
# change.
TIMEOUT_SECONDS = 240


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
    # Invoke via `sys.executable -m maigret` rather than the bare "maigret"
    # command: pip's console-script wrapper for it lands in a Scripts/
    # directory that isn't guaranteed to be on PATH, which makes a plain
    # exec-by-name fail with WinError 2 on Windows. `-m` uses the same
    # interpreter this bot itself runs under, so it always finds the module.
    #
    # --dns-resolver threaded: maigret's default async DNS resolver (aiodns/
    # c-ares) frequently fails to read Windows' real DNS config even when
    # the machine is otherwise online (same root cause as the fix in
    # bot/main.py for the bot's own Telegram connection) — this was
    # observed causing ~87% of site checks to fail as false negatives.
    # The threaded resolver falls back to the OS's own resolution and is
    # reliable everywhere.
    #
    # --no-autoupdate: without it, maigret re-downloads its ~5000-site
    # database on every single run before doing any actual search — slow
    # and was pushing real searches past our own TIMEOUT_SECONDS.
    #
    # PYTHONIOENCODING=utf-8: maigret prints a banner containing a heart
    # symbol (colorama-wrapped) which crashes on Windows' legacy console
    # codepage when stdout has no real console attached (piped) — same
    # class of bug already fixed for blackbird.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "maigret",
        username,
        "-J",
        "simple",
        "-fo",
        str(work_dir),
        "--no-progressbar",
        "--no-color",
        "--dns-resolver",
        "threaded",
        "--no-autoupdate",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("maigret timed out for username=%r", username)
        return ToolResult(tool="maigret", status="timeout", error="Перевищено час очікування")

    result_path = Path(work_dir) / f"report_{username}_simple.json"
    if not result_path.exists():
        logger.warning(
            "maigret failed: no result file; stderr=%r stdout=%r",
            stderr.decode(errors="replace")[:500],
            stdout.decode(errors="replace")[:500],
        )
        return ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено")

    try:
        items = _parse_result_file(result_path)
    except Exception as e:
        logger.warning("maigret failed to parse result file %s: %s", result_path, e)
        return ToolResult(
            tool="maigret", status="failed", error=f"Не вдалося розібрати результат: {e}"
        )
    return ToolResult(tool="maigret", status="ok", items=items)
