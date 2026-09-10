from pathlib import Path

import pytest

from bot.osint import orchestrator
from bot.osint.types import ToolResult


async def test_phone_query_calls_only_phone_runner(monkeypatch):
    monkeypatch.setattr(
        orchestrator, "get_phone_result", lambda q: ToolResult(tool="phone", status="ok")
    )
    results = await orchestrator.run_tools_for_query(
        "+380671234567", "phone", blackbird_dir=Path("."), ghunt_enabled=False
    )
    assert [r.tool for r in results] == ["phone"]


async def test_username_query_calls_three_runners(monkeypatch, tmp_path):
    async def fake_blackbird(username, blackbird_dir):
        return ToolResult(tool="blackbird", status="ok")

    async def fake_maigret(username, work_dir):
        return ToolResult(tool="maigret", status="ok")

    async def fake_sherlock(username, work_dir):
        return ToolResult(tool="sherlock", status="ok")

    monkeypatch.setattr(orchestrator, "run_blackbird", fake_blackbird)
    monkeypatch.setattr(orchestrator, "run_maigret", fake_maigret)
    monkeypatch.setattr(orchestrator, "run_sherlock", fake_sherlock)

    results = await orchestrator.run_tools_for_query(
        "mrmozozavr", "username", blackbird_dir=Path("."), ghunt_enabled=False
    )
    assert {r.tool for r in results} == {"blackbird", "maigret", "sherlock"}


async def test_email_query_without_ghunt_calls_only_holehe(monkeypatch):
    async def fake_holehe(email, work_dir):
        return ToolResult(tool="holehe", status="ok")

    monkeypatch.setattr(orchestrator, "run_holehe", fake_holehe)

    results = await orchestrator.run_tools_for_query(
        "user@example.com", "email", blackbird_dir=Path("."), ghunt_enabled=False
    )
    assert [r.tool for r in results] == ["holehe"]


async def test_gmail_query_with_ghunt_enabled_calls_both(monkeypatch):
    async def fake_holehe(email, work_dir):
        return ToolResult(tool="holehe", status="ok")

    async def fake_ghunt(email, work_dir):
        return ToolResult(tool="ghunt", status="ok")

    monkeypatch.setattr(orchestrator, "run_holehe", fake_holehe)
    monkeypatch.setattr(orchestrator, "run_ghunt", fake_ghunt)

    results = await orchestrator.run_tools_for_query(
        "user@gmail.com", "email", blackbird_dir=Path("."), ghunt_enabled=True
    )
    assert {r.tool for r in results} == {"holehe", "ghunt"}


async def test_non_gmail_query_with_ghunt_enabled_skips_ghunt(monkeypatch):
    async def fake_holehe(email, work_dir):
        return ToolResult(tool="holehe", status="ok")

    monkeypatch.setattr(orchestrator, "run_holehe", fake_holehe)

    results = await orchestrator.run_tools_for_query(
        "user@yahoo.com", "email", blackbird_dir=Path("."), ghunt_enabled=True
    )
    assert [r.tool for r in results] == ["holehe"]


async def test_unknown_query_type_raises():
    with pytest.raises(ValueError):
        await orchestrator.run_tools_for_query(
            "x", "carrier-pigeon", blackbird_dir=Path("."), ghunt_enabled=False
        )


async def test_one_runner_crashing_does_not_kill_the_other_results(monkeypatch):
    """Regression test: per spec, one tool crashing must degrade to a
    "failed" marker for that tool while the others still complete - it
    must not blow up the whole search via an uncaught asyncio.gather
    exception."""

    async def fake_blackbird(username, blackbird_dir):
        raise RuntimeError("boom: blackbird exploded before parsing anything")

    async def fake_maigret(username, work_dir):
        return ToolResult(tool="maigret", status="ok", items=[{"label": "x", "value": "y"}])

    async def fake_sherlock(username, work_dir):
        return ToolResult(tool="sherlock", status="ok")

    monkeypatch.setattr(orchestrator, "run_blackbird", fake_blackbird)
    monkeypatch.setattr(orchestrator, "run_maigret", fake_maigret)
    monkeypatch.setattr(orchestrator, "run_sherlock", fake_sherlock)

    results = await orchestrator.run_tools_for_query(
        "mrmozozavr", "username", blackbird_dir=Path("."), ghunt_enabled=False
    )

    by_tool = {r.tool: r for r in results}
    assert set(by_tool) == {"blackbird", "maigret", "sherlock"}
    assert by_tool["blackbird"].status == "failed"
    assert "boom" in by_tool["blackbird"].error
    assert by_tool["maigret"].status == "ok"
    assert by_tool["sherlock"].status == "ok"
