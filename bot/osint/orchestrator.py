import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Coroutine

from bot.osint.runners.blackbird import run_blackbird
from bot.osint.runners.ghunt import run_ghunt
from bot.osint.runners.holehe import run_holehe
from bot.osint.runners.maigret import run_maigret
from bot.osint.runners.phone import get_phone_result
from bot.osint.runners.sherlock import run_sherlock
from bot.osint.types import ToolResult


async def _gather_tool_results(tasks: list[tuple[str, Coroutine]]) -> list[ToolResult]:
    """Run tool coroutines concurrently and never let one tool's crash take
    down the others.

    return_exceptions=True stops asyncio.gather from propagating an
    exception raised by any single coroutine (e.g. a subprocess-creation
    failure that happens before a runner even gets to its own
    try/except around _parse_result_file). This is a safety net on top of
    each runner's own internal guarding: any raw Exception that still
    slips through is converted into a "failed" ToolResult here, so the
    other tools' results are still delivered - per spec, one broken tool
    must show as a marker in the report, not sink the whole search.
    """
    names = [name for name, _ in tasks]
    coros = [coro for _, coro in tasks]
    raw_results = await asyncio.gather(*coros, return_exceptions=True)

    results: list[ToolResult] = []
    for name, raw in zip(names, raw_results):
        if isinstance(raw, BaseException):
            results.append(ToolResult(tool=name, status="failed", error=str(raw)))
        else:
            results.append(raw)
    return results


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
            return await _gather_tool_results(
                [
                    ("blackbird", run_blackbird(query, blackbird_dir)),
                    ("maigret", run_maigret(query, work_dir)),
                    ("sherlock", run_sherlock(query, work_dir)),
                ]
            )

        tasks = [("holehe", run_holehe(query, work_dir))]
        if ghunt_enabled and query.lower().endswith("@gmail.com"):
            tasks.append(("ghunt", run_ghunt(query, work_dir)))
        return await _gather_tool_results(tasks)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
