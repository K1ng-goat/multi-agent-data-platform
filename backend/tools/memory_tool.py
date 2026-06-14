"""MemoryTool — memory persistence operations."""
from __future__ import annotations
from .base_tool import BaseTool
from .registry import tool_registry


class MemoryTool(BaseTool):
    name = "MemoryTool"
    description = "Save and retrieve analysis memories"

    def execute(self, **kwargs) -> dict:
        action = kwargs.get("action", "save")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id", "")
        data = kwargs.get("data", {})

        from memory.memory_manager import get_memory_manager
        mgr = get_memory_manager()

        if action == "save_workspace":
            mgr.save_workspace(user_id, session_id,
                               data.get("filename", ""),
                               data.get("data_summary", {}),
                               data.get("charts", []),
                               data.get("analysis", {}),
                               data.get("active_theme", "business"))
        elif action == "save_analysis":
            mgr.save_analysis_memory(user_id, session_id,
                                     data.get("filename", ""),
                                     data.get("analysis", {}),
                                     data.get("charts", []))
        elif action == "get_preferences":
            return {"ok": True, "preferences": mgr.get_user_preferences(user_id)}
        elif action == "get_summary":
            return {"ok": True, **mgr.get_memory_summary(user_id)}
        else:
            return {"ok": False, "error": f"unknown action: {action}"}

        return {"ok": True}


tool_registry.register(MemoryTool())
