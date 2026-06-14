"""ToolRegistry — dynamic tool discovery and lookup."""
from __future__ import annotations
from .base_tool import BaseTool


class ToolRegistry:
    """Central tool registry.  Tools self-register via register()."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        print(f"[ToolRegistry] registered: {tool.name}")

    def get(self, name: str) -> BaseTool:
        """Get a tool by name."""
        return self._tools[name]

    def list_tools(self) -> list[dict]:
        """List all registered tools with metadata."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)


# ── Singleton ─────────────────────────────────────────────

tool_registry = ToolRegistry()
