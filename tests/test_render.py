from pathlib import Path

from bot.osint.types import ToolResult
from bot.report.render import render_report


def test_render_report_creates_html_file(tmp_path):
    results = [
        ToolResult(
            tool="blackbird",
            status="ok",
            items=[{"label": "GitHub", "value": "https://github.com/mrmozozavr"}],
        ),
        ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено"),
    ]

    out_path = render_report("mrmozozavr", "username", results, reports_dir=tmp_path)

    assert out_path.exists()
    assert out_path.suffix == ".html"
    content = out_path.read_text(encoding="utf-8")
    assert "mrmozozavr" in content
    assert "github.com/mrmozozavr" in content
    assert "НЕДОСТУПНО" in content
    assert "Файл результатів не знайдено" in content


def test_render_report_empty_items_shows_not_found_message(tmp_path):
    results = [ToolResult(tool="holehe", status="ok", items=[])]
    out_path = render_report("user@example.com", "email", results, reports_dir=tmp_path)
    content = out_path.read_text(encoding="utf-8")
    assert "Нічого не знайдено" in content
