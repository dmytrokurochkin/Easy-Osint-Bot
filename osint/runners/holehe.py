import asyncio
import csv
import glob
import logging
import os
import sys
import sysconfig
from pathlib import Path

from osint.types import ToolResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120


def _holehe_command() -> str:
    """Resolve the holehe executable without depending on PATH.

    holehe has no `__main__.py`, so unlike maigret/sherlock it can't be run
    via `-m`. pip's console-script wrapper for it lands in this
    interpreter's Scripts/bin directory, which isn't guaranteed to be on
    PATH (the bare "holehe" command then fails with WinError 2 on Windows).
    Resolve the wrapper's real path directly; fall back to the bare command
    name if that file doesn't exist (e.g. a different install layout where
    PATH already works).
    """
    scripts_dir = Path(sysconfig.get_path("scripts"))
    exe_name = "holehe.exe" if sys.platform == "win32" else "holehe"
    resolved = scripts_dir / exe_name
    return str(resolved) if resolved.exists() else "holehe"


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
    # PYTHONIOENCODING=utf-8 pre-empts the same Windows-console Unicode
    # crash already confirmed for blackbird and maigret.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = await asyncio.create_subprocess_exec(
        _holehe_command(),
        email,
        "--csv",
        "--no-color",
        cwd=str(work_dir),
        env=env,
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
