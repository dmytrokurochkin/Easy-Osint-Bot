from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from bot.osint.types import ToolResult

TEMPLATE_DIR = Path(__file__).parent

TOOL_NAMES = {
    "blackbird": "Blackbird",
    "maigret": "Maigret",
    "sherlock": "Sherlock",
    "holehe": "Holehe",
    "ghunt": "GHunt",
    "phone": "Номер телефону",
}


def render_report(
    query: str, query_type: str, results: list[ToolResult], reports_dir: Path
) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html.j2")
    html = template.render(
        query=query,
        query_type=query_type,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        results=results,
        tool_names=TOOL_NAMES,
    )

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_query = "".join(c if c.isalnum() else "_" for c in query)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"{timestamp}_{safe_query}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
