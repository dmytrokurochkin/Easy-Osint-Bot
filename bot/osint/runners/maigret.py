import asyncio
import json
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


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
    proc = await asyncio.create_subprocess_exec(
        "maigret",
        username,
        "-J",
        "simple",
        "-fo",
        str(work_dir),
        "--no-progressbar",
        "--no-color",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="maigret", status="timeout", error="Перевищено час очікування")

    result_path = Path(work_dir) / f"report_{username}_simple.json"
    if not result_path.exists():
        return ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено")

    items = _parse_result_file(result_path)
    return ToolResult(tool="maigret", status="ok", items=items)
