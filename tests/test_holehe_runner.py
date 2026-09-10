import shutil
from pathlib import Path

from bot.osint.runners import holehe

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_holehe_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)  # holehe always exits 1 on success, see spec
    email = "mrmozozavr@example.com"
    shutil.copy(
        FIXTURES_DIR / "holehe_result.csv",
        tmp_path / f"holehe_1234567890_{email}_results.csv",
    )

    result = await holehe.run_holehe(email, tmp_path)

    assert result.tool == "holehe"
    assert result.status == "ok"
    assert len(result.items) == 2  # only exists == True rows
    github_item = next(i for i in result.items if i["label"] == "github")
    assert github_item["value"] == "знайдено"
    discord_item = next(i for i in result.items if i["label"] == "discord")
    assert "t***@gmail.com" in discord_item["value"]


async def test_run_holehe_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)
    result = await holehe.run_holehe("nobody@example.com", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_holehe_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(holehe, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await holehe.run_holehe("mrmozozavr@example.com", tmp_path)
    assert result.status == "timeout"


async def test_run_holehe_malformed_result_file_is_failed_not_raised(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)
    email = "mrmozozavr@example.com"
    # Invalid UTF-8 bytes make the file unreadable with the runner's fixed
    # encoding="utf-8", exercising the _parse_result_file exception path.
    (tmp_path / f"holehe_1234567890_{email}_results.csv").write_bytes(
        b"exists\n\xff\xfe\x00broken"
    )

    result = await holehe.run_holehe(email, tmp_path)

    assert result.status == "failed"
    assert result.error
