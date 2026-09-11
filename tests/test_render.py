from pathlib import Path

from osint.types import ToolResult
from report.render import render_report


def test_render_report_creates_html_file(tmp_path):
    results = [
        ToolResult(
            tool="blackbird",
            status="ok",
            items=[{"label": "GitHub", "value": "https://github.com/mrmozozavr"}],
        ),
        ToolResult(tool="maigret", status="failed", error="Файл результатів не знайдено"),
    ]

    out_path = render_report("mrmozozavr", "username", results, reports_dir=tmp_path, lang="uk")

    assert out_path.exists()
    assert out_path.suffix == ".html"
    content = out_path.read_text(encoding="utf-8")
    assert "mrmozozavr" in content
    assert "github.com/mrmozozavr" in content
    assert "НЕДОСТУПНО" in content
    assert "Файл результатів не знайдено" in content


def test_render_report_empty_items_shows_not_found_message(tmp_path):
    results = [ToolResult(tool="holehe", status="ok", items=[])]
    out_path = render_report("user@example.com", "email", results, reports_dir=tmp_path, lang="uk")
    content = out_path.read_text(encoding="utf-8")
    assert "Нічого не знайдено" in content


def test_render_report_escapes_untrusted_tool_output(tmp_path):
    payload = "<script>alert(1)</script>"
    results = [
        ToolResult(
            tool="holehe",
            status="ok",
            items=[{"label": "email", "value": payload}],
        ),
    ]

    out_path = render_report(payload, "username", results, reports_dir=tmp_path, lang="uk")

    content = out_path.read_text(encoding="utf-8")
    assert payload not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


def test_render_report_respects_language(tmp_path):
    results = [ToolResult(tool="holehe", status="ok", items=[])]
    out_path_en = render_report(
        "user@example.com", "email", results, reports_dir=tmp_path, lang="en"
    )
    content_en = out_path_en.read_text(encoding="utf-8")
    assert "Nothing found." in content_en
    assert "OSINT Report: user@example.com" in content_en


def test_render_report_phone_tool_name_is_localized(tmp_path):
    results = [ToolResult(tool="phone", status="ok", items=[{"label": "Region", "value": "UA"}])]
    out_path = render_report("+380001112233", "phone", results, reports_dir=tmp_path, lang="pl")
    content = out_path.read_text(encoding="utf-8")
    assert "Numer telefonu" in content
