import asyncio
import logging
from pathlib import Path

from osint.types import ToolResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120


def _dig(data: dict, path: list[str]):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _parse_result_file(path: Path) -> list[dict]:
    import json

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profile_container = data.get("PROFILE_CONTAINER")
    if not profile_container:
        return []

    profile = profile_container.get("profile") or {}
    items = []

    full_name = _dig(profile, ["names", "PROFILE", "fullname"])
    if full_name:
        items.append({"label": "Ім'я профілю", "value": full_name})

    gaia_id = profile.get("personId")
    if gaia_id:
        items.append({"label": "Gaia ID", "value": str(gaia_id)})

    photo_url = _dig(profile, ["profilePhotos", "PROFILE", "url"])
    if photo_url:
        items.append({"label": "Фото профілю", "value": photo_url})

    if (profile_container.get("maps") or {}).get("stats"):
        items.append({"label": "Google Maps активність", "value": "знайдено"})

    if profile_container.get("calendar"):
        items.append({"label": "Публічний Google Calendar", "value": "знайдено"})

    return items


async def run_ghunt(email: str, work_dir: Path) -> ToolResult:
    json_path = Path(work_dir) / "ghunt_result.json"

    proc = await asyncio.create_subprocess_exec(
        "ghunt",
        "email",
        email,
        "--json",
        str(json_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("ghunt timed out for email=%r", email)
        return ToolResult(tool="ghunt", status="timeout", error="Перевищено час очікування")

    if not json_path.exists():
        logger.warning(
            "ghunt failed: no result file; stderr=%r stdout=%r",
            stderr.decode(errors="replace")[:500],
            stdout.decode(errors="replace")[:500],
        )
        return ToolResult(
            tool="ghunt", status="failed", error="GHunt не авторизований або ціль не знайдена"
        )

    try:
        items = _parse_result_file(json_path)
    except Exception as e:
        logger.warning("ghunt failed to parse result file %s: %s", json_path, e)
        return ToolResult(
            tool="ghunt", status="failed", error=f"Не вдалося розібрати результат: {e}"
        )
    return ToolResult(tool="ghunt", status="ok", items=items)
