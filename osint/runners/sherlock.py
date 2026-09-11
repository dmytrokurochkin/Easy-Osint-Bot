import asyncio
import csv
import logging
import os
import sys
from pathlib import Path

from osint.types import ToolResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("exists") != "Claimed":
                continue
            items.append({"label": row.get("name", "unknown"), "value": row.get("url_user", "")})
    return items


async def run_sherlock(username: str, work_dir: Path) -> ToolResult:
    # Same reasoning as maigret's runner: invoke via `-m` on this bot's own
    # interpreter instead of the bare "sherlock" command, which depends on
    # a Scripts/ directory that may not be on PATH (WinError 2 on Windows).
    # PYTHONIOENCODING=utf-8 pre-empts the same Windows-console Unicode
    # crash already confirmed for blackbird and maigret.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "sherlock_project",
        username,
        "--csv",
        "--folderoutput",
        str(work_dir),
        "--timeout",
        "60",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("sherlock timed out for username=%r", username)
        return ToolResult(tool="sherlock", status="timeout", error="Перевищено час очікування")

    result_path = Path(work_dir) / f"{username}.csv"
    if not result_path.exists():
        logger.warning(
            "sherlock failed: no result file; stderr=%r stdout=%r",
            stderr.decode(errors="replace")[:500],
            stdout.decode(errors="replace")[:500],
        )
        return ToolResult(tool="sherlock", status="failed", error="Файл результатів не знайдено")

    try:
        items = _parse_result_file(result_path)
    except Exception as e:
        logger.warning("sherlock failed to parse result file %s: %s", result_path, e)
        return ToolResult(
            tool="sherlock", status="failed", error=f"Не вдалося розібрати результат: {e}"
        )
    return ToolResult(tool="sherlock", status="ok", items=items)
