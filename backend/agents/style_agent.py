"""StyleAgent — wraps theme_service functions for style detection and application."""
from .base_agent import BaseAgent


class StyleAgent(BaseAgent):
    name = "StyleAgent"
    description = "文档样式识别与管理"

    async def execute(self, context: dict) -> dict:
        user_message = context.get("user_message", "")
        if not user_message:
            self.add_step(context, "done", "无样式指令，跳过")
            return context

        self.add_step(context, "running", "检测样式意图...")

        try:
            import theme_service as ts

            if not ts.detect_style_intent(user_message):
                self.add_step(context, "done", "未检测到样式相关指令")
                return context

            overrides = ts.quick_parse_style(user_message)
            if not overrides:
                self.add_step(context, "done", "未解析到样式参数")
                return context

            theme_name = overrides.pop("_theme", None)
            style_config = {
                "_theme": theme_name,
                "overrides": overrides,
            }
            context["style"] = style_config

            lines = []
            if theme_name:
                theme = ts.THEMES.get(theme_name, {})
                lines.append(f"主题: {theme.get('name', theme_name)}")
            for k, v in overrides.items():
                if not k.startswith("_"):
                    lines.append(f"{k} = {v}")

            self.add_step(context, "done", f"样式设置完成: {'; '.join(lines)}" if lines else "样式设置完成")
        except Exception as e:
            self.add_step(context, "error", f"样式处理失败: {str(e)}")
            context.setdefault("errors", []).append(f"StyleAgent: {str(e)}")

        return context

    def detect_style_intent(self, user_message: str) -> bool:
        """Check if message contains style-related instructions."""
        import theme_service as ts
        return ts.detect_style_intent(user_message)

    def parse_style(self, user_message: str) -> dict:
        """Parse style parameters from user message."""
        import theme_service as ts
        return ts.quick_parse_style(user_message)
