import shutil
from pathlib import Path

from bot.osint.runners import sherlock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_sherlock_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    shutil.copy(FIXTURES_DIR / "sherlock_result.csv", tmp_path / f"{username}.csv")

    result = await sherlock.run_sherlock(username, tmp_path)

    assert result.tool == "sherlock"
    assert result.status == "ok"
    assert {"label": "GitHub", "value": "https://www.github.com/mrmozozavr"} in result.items
    assert len(result.items) == 1  # "Available" row excluded


async def test_run_sherlock_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    result = await sherlock.run_sherlock("nobody", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_sherlock_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(sherlock, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await sherlock.run_sherlock("mrmozozavr", tmp_path)
    assert result.status == "timeout"


async def test_run_sherlock_malformed_result_file_is_failed_not_raised(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)
    username = "mrmozozavr"
    # Invalid UTF-8 bytes make the file unreadable with the runner's fixed
    # encoding="utf-8", exercising the _parse_result_file exception path.
    (tmp_path / f"{username}.csv").write_bytes(b"exists\n\xff\xfe\x00broken")

    result = await sherlock.run_sherlock(username, tmp_path)

    assert result.status == "failed"
    assert result.error
