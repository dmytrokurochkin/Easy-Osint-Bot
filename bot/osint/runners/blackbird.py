import asyncio
import json
from datetime import datetime
from pathlib import Path

from bot.osint.types import ToolResult

TIMEOUT_SECONDS = 120


def _parse_result_file(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [{"label": entry["name"], "value": entry["url"]} for entry in data]


async def run_blackbird(username: str, blackbird_dir: Path) -> ToolResult:
    date_raw = datetime.now().strftime("%m_%d_%Y")

    proc = await asyncio.create_subprocess_exec(
        "python",
        "blackbird.py",
        "--username",
        username,
        "--json",
        cwd=str(blackbird_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(tool="blackbird", status="timeout", error="Перевищено час очікування")

    result_path = (
        Path(blackbird_dir)
        / "results"
        / f"{username}_{date_raw}_blackbird"
        / f"{username}_{date_raw}_blackbird.json"
    )
    if not result_path.exists():
        return ToolResult(tool="blackbird", status="failed", error="Файл результатів не знайдено")

    items = _parse_result_file(result_path)
    return ToolResult(tool="blackbird", status="ok", items=items)
