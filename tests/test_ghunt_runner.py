import shutil
from pathlib import Path

from osint.runners import ghunt

FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_run_ghunt_parses_result_file(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)

    async def fake_create(*args, **kwargs):
        # simulate ghunt writing its output file as a side effect of running
        shutil.copy(FIXTURES_DIR / "ghunt_result.json", tmp_path / "ghunt_result.json")
        from tests.conftest import FakeProcess

        return FakeProcess(returncode=0)

    import asyncio

    import pytest

    monkeypatch_target = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = fake_create
    try:
        result = await ghunt.run_ghunt("target@gmail.com", tmp_path)
    finally:
        asyncio.create_subprocess_exec = monkeypatch_target

    assert result.tool == "ghunt"
    assert result.status == "ok"
    assert {"label": "Ім'я профілю", "value": "Mr Mozozavr"} in result.items
    assert {"label": "Gaia ID", "value": "1234567890"} in result.items
    assert any(item["label"] == "Google Maps активність" for item in result.items)


async def test_run_ghunt_missing_result_file_is_failed(tmp_path, fake_subprocess):
    fake_subprocess(returncode=1)
    result = await ghunt.run_ghunt("nobody@gmail.com", tmp_path)
    assert result.status == "failed"
    assert result.error


async def test_run_ghunt_sets_pythonioencoding_utf8(tmp_path):
    import asyncio

    from tests.conftest import FakeProcess

    captured_kwargs = {}

    async def fake_create(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return FakeProcess(returncode=1)

    monkeypatch_target = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = fake_create
    try:
        await ghunt.run_ghunt("nobody@gmail.com", tmp_path)
    finally:
        asyncio.create_subprocess_exec = monkeypatch_target

    # GHunt's rich banner crashes on Windows when this isn't set (emoji vs
    # the cp1252 fallback encoding rich uses without a detected console) -
    # see the comment in osint/runners/ghunt.py.
    assert captured_kwargs["env"]["PYTHONIOENCODING"] == "utf-8"


async def test_run_ghunt_timeout(tmp_path, fake_subprocess, monkeypatch):
    monkeypatch.setattr(ghunt, "TIMEOUT_SECONDS", 0.05)
    fake_subprocess(sleep=1)
    result = await ghunt.run_ghunt("target@gmail.com", tmp_path)
    assert result.status == "timeout"


async def test_run_ghunt_malformed_result_file_is_failed_not_raised(tmp_path, fake_subprocess):
    fake_subprocess(returncode=0)

    async def fake_create(*args, **kwargs):
        (tmp_path / "ghunt_result.json").write_text("{not valid json", encoding="utf-8")
        from tests.conftest import FakeProcess

        return FakeProcess(returncode=0)

    import asyncio

    monkeypatch_target = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = fake_create
    try:
        result = await ghunt.run_ghunt("target@gmail.com", tmp_path)
    finally:
        asyncio.create_subprocess_exec = monkeypatch_target

    assert result.status == "failed"
    assert result.error
