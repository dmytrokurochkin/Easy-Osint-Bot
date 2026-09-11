from dataclasses import dataclass, field


@dataclass
class ToolResult:
    tool: str
    status: str  # "ok" | "failed" | "timeout"
    items: list[dict] = field(default_factory=list)
    error: str | None = None
