import shutil
from datetime import datetime
from pathlib import Path

import pytest

from bot.osint.runners import blackbird

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _date_raw() -> str:
    return datetime.now().strftime("%m_%d_%Y")


async def test_run_blackbird_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    result_dir = tmp_path / "results" / f"{username}_{_date_raw()}_blackbird"
    result_dir.mkdir(parents=True)
    result_file = result_dir / f"{username}_{_date_raw()}_blackbird.json"
    shutil.copy(FIXTURES_DIR / "blackbird_result.json", result_file)

    result = await blackbird.run_blackbird(username, tmp_path)

    assert result.tool == "blackbird"
    assert result.status == "ok"
    assert {"label": "GitHub (User)", "value": "https://api.github.com/users/mrmozozavr"} in result.items
    assert len(result.items) == 2


async def test_run_blackbird_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    result = await blackbird.run_blackbird("nobody", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_blackbird_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(blackbird, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await blackbird.run_blackbird("mrmozozavr", tmp_path)
    assert result.status == "timeout"
