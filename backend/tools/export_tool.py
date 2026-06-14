"""ExportTool — file export operations."""
from __future__ import annotations
from .base_tool import BaseTool
from .registry import tool_registry


class ExportTool(BaseTool):
    name = "ExportTool"
    description = "Export data to Excel, Word, and chart images"

    def execute(self, **kwargs) -> dict:
        action = kwargs.get("action", "")
        session = kwargs.get("session", {})
        if not session:
            return {"ok": False, "error": "session required"}

        import export_service as es
        if action == "excel":
            path = es.export_excel(session)
        elif action == "word":
            path = es.export_word(session)
        elif action == "chart":
            chart_config = kwargs.get("chart_config")
            idx = kwargs.get("index", 0)
            path = es.export_chart(chart_config, idx, es._base_name(session), "png", session=session)
        else:
            return {"ok": False, "error": f"unknown action: {action}"}

        return {"ok": True, "path": path}


tool_registry.register(ExportTool())
