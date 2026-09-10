import asyncio
import shutil
import tempfile
from pathlib import Path

from bot.osint.runners.blackbird import run_blackbird
from bot.osint.runners.ghunt import run_ghunt
from bot.osint.runners.holehe import run_holehe
from bot.osint.runners.maigret import run_maigret
from bot.osint.runners.phone import get_phone_result
from bot.osint.runners.sherlock import run_sherlock
from bot.osint.types import ToolResult


async def run_tools_for_query(
    query: str, query_type: str, blackbird_dir: Path, ghunt_enabled: bool
) -> list[ToolResult]:
    if query_type == "phone":
        return [get_phone_result(query)]

    if query_type not in ("username", "email"):
        raise ValueError(f"Unknown query_type: {query_type}")

    work_dir = Path(tempfile.mkdtemp(prefix="osint_"))
    try:
        if query_type == "username":
            results = await asyncio.gather(
                run_blackbird(query, blackbird_dir),
                run_maigret(query, work_dir),
                run_sherlock(query, work_dir),
            )
            return list(results)

        tasks = [run_holehe(query, work_dir)]
        if ghunt_enabled and query.lower().endswith("@gmail.com"):
            tasks.append(run_ghunt(query, work_dir))
        results = await asyncio.gather(*tasks)
        return list(results)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
