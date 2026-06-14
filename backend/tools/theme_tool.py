"""ThemeTool — style and theme operations."""
from __future__ import annotations
from .base_tool import BaseTool
from .registry import tool_registry


class ThemeTool(BaseTool):
    name = "ThemeTool"
    description = "Apply and list document style themes"

    def execute(self, **kwargs) -> dict:
        action = kwargs.get("action", "list")
        import theme_service as ts

        if action == "list":
            themes = [
                {"id": k, "name": v["name"], "description": v["description"]}
                for k, v in ts.THEMES.items()
            ]
            return {"ok": True, "themes": themes, "current_default": "business"}

        if action == "apply":
            session = kwargs.get("session", {})
            theme = kwargs.get("theme", "business")
            overrides = kwargs.get("overrides", {})
            if theme in ts.THEMES:
                session["active_theme"] = theme
            if overrides:
                session.setdefault("style_overrides", {}).update(overrides)
            return {"ok": True, "active_theme": session.get("active_theme", theme)}

        if action == "detect_intent":
            message = kwargs.get("message", "")
            return {"ok": True, "has_style_intent": ts.detect_style_intent(message)}

        return {"ok": False, "error": f"unknown action: {action}"}


tool_registry.register(ThemeTool())
