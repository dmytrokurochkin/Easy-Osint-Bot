import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from locales import get_text
from osint.types import ToolResult

TEMPLATE_DIR = Path(__file__).parent

_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _is_url(value: str) -> bool:
    return bool(_URL_RE.match(value))

# Proper nouns / brand names - identical across every supported language.
STATIC_TOOL_NAMES = {
    "blackbird": "Blackbird",
    "maigret": "Maigret",
    "sherlock": "Sherlock",
    "holehe": "Holehe",
    "ghunt": "GHunt",
}

QUERY_TYPE_LABEL_KEYS = {
    "email": "query_type_email",
    "phone": "query_type_phone",
    "username": "query_type_username",
}


def _tool_names(lang: str) -> dict[str, str]:
    names = dict(STATIC_TOOL_NAMES)
    names["phone"] = get_text(lang, "tool_phone")
    return names


def render_report(
    query: str, query_type: str, results: list[ToolResult], reports_dir: Path, lang: str
) -> Path:
    # Unconditional autoescape: select_autoescape() decides by filename suffix,
    # and this module's template is named "template.html.j2" (suffix ".j2"),
    # which select_autoescape would NOT recognize as HTML - silently disabling
    # escaping of untrusted OSINT tool output. This module only ever renders
    # this one (always-HTML) template, so autoescape=True is always correct.
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    env.tests["url"] = _is_url
    template = env.get_template("template.html.j2")
    html = template.render(
        lang=lang,
        report_title=get_text(lang, "report_title", query=query),
        query_type_label=get_text(lang, QUERY_TYPE_LABEL_KEYS[query_type]),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        results=results,
        tool_names=_tool_names(lang),
        status_ok_label=get_text(lang, "report_status_ok"),
        status_unavailable_label=get_text(lang, "report_status_unavailable"),
        nothing_found_label=get_text(lang, "report_nothing_found"),
        tool_unavailable_label=get_text(lang, "report_tool_unavailable"),
        footer_label=get_text(lang, "report_footer"),
    )

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_query = "".join(c if c.isalnum() else "_" for c in query)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"{timestamp}_{safe_query}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
