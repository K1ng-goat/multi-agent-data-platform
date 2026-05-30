"""Base Agent class — all sub-agents inherit from this."""


class BaseAgent:
    name: str = "base"
    description: str = ""

    async def execute(self, context: dict) -> dict:
        """Execute agent logic. Input/Output: context dict."""
        raise NotImplementedError

    def add_step(self, context: dict, status: str, message: str):
        """Append an execution step record to context['steps'] for frontend visualization."""
        context.setdefault("steps", []).append({
            "agent": self.name,
            "status": status,
            "message": message,
        })
