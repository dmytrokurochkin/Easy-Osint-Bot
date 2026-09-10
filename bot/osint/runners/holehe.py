import asyncio
import csv
import glob
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
            if row.get("exists") != "True":
                continue
            extras = []
            if row.get("emailrecovery"):
                extras.append(f"відновлення: {row['emailrecovery']}")
            if row.get("phoneNumber"):
                extras.append(f"телефон: {row['phoneNumber']}")
            value = "знайдено" + (" · " + ", ".join(extras) if extras else "")
            items.append({"label": row.get("name", "unknown"), "value": value})
    return items


async def run_holehe(email: str, work_dir: Path) -> ToolResult:
    # holehe writes its CSV to the process's cwd and calls exit() with a
    # string message on success, which always yields returncode=1 — success
    # is therefore judged by the output file's existence, not the exit code.
    proc = await asyncio.create_subprocess_exec(
        "holehe",
        email,
        "--csv",
        "--no-color",
        cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("holehe timed out for email=%r", email)
        return ToolResult(tool="holehe", status="timeout", error="Перевищено час очікування")

    matches = glob.glob(str(Path(work_dir) / f"holehe_*_{email}_results.csv"))
    if not matches:
        logger.warning(
            "holehe failed: no result file; stderr=%r stdout=%r",
            stderr.decode(errors="replace")[:500],
            stdout.decode(errors="replace")[:500],
        )
        return ToolResult(tool="holehe", status="failed", error="Файл результатів не знайдено")

    try:
        items = _parse_result_file(Path(matches[0]))
    except Exception as e:
        logger.warning("holehe failed to parse result file %s: %s", matches[0], e)
        return ToolResult(
            tool="holehe", status="failed", error=f"Не вдалося розібрати результат: {e}"
        )
    return ToolResult(tool="holehe", status="ok", items=items)
