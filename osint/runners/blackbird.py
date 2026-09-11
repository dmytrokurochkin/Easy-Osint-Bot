import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from osint.types import ToolResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [{"label": entry["name"], "value": entry["url"]} for entry in data]


async def run_blackbird(username: str, blackbird_dir: Path) -> ToolResult:
    date_raw = datetime.now().strftime("%m_%d_%Y")

    # blackbird prints an ASCII-art banner full of block-drawing characters
    # on every run. On Windows, when stdout is piped (no real console
    # attached), Python falls back to the system's legacy codepage (e.g.
    # cp1252), which can't encode those characters and crashes blackbird
    # before it does anything. Force UTF-8 for the child process.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "blackbird.py",
        "--username",
        username,
        "--json",
        cwd=str(blackbird_dir),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("blackbird timed out for username=%r", username)
        return ToolResult(tool="blackbird", status="timeout", error="Перевищено час очікування")

    result_path = (
        Path(blackbird_dir)
        / "results"
        / f"{username}_{date_raw}_blackbird"
        / f"{username}_{date_raw}_blackbird.json"
    )
    if not result_path.exists():
        # blackbird only writes the JSON file when it found at least one
        # account (see src/modules/export/json.py: it's called behind
        # `if config.json and config.usernameFoundAccounts`). A clean exit
        # with no file means "zero matches", not a failure — only a
        # non-zero exit code means blackbird actually crashed.
        if proc.returncode == 0:
            return ToolResult(tool="blackbird", status="ok", items=[])
        logger.warning(
            "blackbird failed: no result file; stderr=%r stdout=%r",
            stderr.decode(errors="replace")[:500],
            stdout.decode(errors="replace")[:500],
        )
        return ToolResult(tool="blackbird", status="failed", error="Файл результатів не знайдено")

    try:
        items = _parse_result_file(result_path)
    except Exception as e:
        logger.warning("blackbird failed to parse result file %s: %s", result_path, e)
        return ToolResult(
            tool="blackbird", status="failed", error=f"Не вдалося розібрати результат: {e}"
        )
    return ToolResult(tool="blackbird", status="ok", items=items)
