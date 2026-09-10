import shutil
from pathlib import Path

from bot.osint.runners import maigret

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_maigret_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    shutil.copy(
        FIXTURES_DIR / "maigret_result.json",
        tmp_path / f"report_{username}_simple.json",
    )

    result = await maigret.run_maigret(username, tmp_path)

    assert result.tool == "maigret"
    assert result.status == "ok"
    assert {"label": "GitHub", "value": "https://github.com/mrmozozavr"} in result.items
    assert len(result.items) == 2


async def test_run_maigret_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    result = await maigret.run_maigret("nobody", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_maigret_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(maigret, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await maigret.run_maigret("mrmozozavr", tmp_path)
    assert result.status == "timeout"
