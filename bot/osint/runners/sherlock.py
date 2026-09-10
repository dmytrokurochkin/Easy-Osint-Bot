import asyncio
import csv
import logging
from pathlib import Path

from bot.osint.types import ToolResult

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
    proc = await asyncio.create_subprocess_exec(
        "sherlock",
        username,
        "--csv",
        "--folderoutput",
        str(work_dir),
        "--timeout",
        "60",
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
