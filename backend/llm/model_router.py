"""ModelRouter — maps task types to LLM providers.

All routes currently return DeepSeek. Future providers (OpenAI, Claude)
are registered as stubs and will activate when API keys are present.
"""
from __future__ import annotations
import os
from .base_provider import BaseLLMProvider
from .deepseek_provider import DeepSeekProvider
from .provider_registry import provider_registry


# ── Future Provider Stubs ────────────────────────────────

class _StubProvider(BaseLLMProvider):
    """Placeholder for future providers. Returns disabled status."""
    enabled = False

    def __init__(self, name: str): self.name = name

    async def generate(self, prompt: str, **kwargs) -> str:
        return ""

    def status(self) -> dict:
        return {"id": self.name, "enabled": False, "reason": "API key missing"}


# ── Router ───────────────────────────────────────────────

class ModelRouter:
    """Routes task types to the best available LLM provider.

    All routes default to DeepSeek. Stubs for OpenAI, Claude, Gemini,
    Qwen are registered but disabled (API key not configured).
    """

    def __init__(self):
        # Register DeepSeek (always enabled when key is present)
        ds = DeepSeekProvider()
        ds.enabled = bool(os.getenv("DEEPSEEK_API_KEY", ""))
        provider_registry.register(ds)

        # Future stubs (disabled)
        for name in ["openai", "claude", "gemini", "qwen"]:
            provider_registry.register(_StubProvider(name))

    def route(self, task_type: str) -> str:
        """Return the provider name for a task type. Always DeepSeek for now."""
        enabled = provider_registry.get_enabled()
        if "deepseek" in enabled:
            return "deepseek"
        return enabled[0] if enabled else "deepseek"

    def get_routing_map(self) -> dict[str, str]:
        """Return the full routing table."""
        tasks = ["chat", "analysis", "planner", "report", "audit"]
        return {t: self.route(t) for t in tasks}


# ── Singleton ─────────────────────────────────────────────

model_router = ModelRouter()
