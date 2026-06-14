"""ProviderRegistry — manages LLM provider registration and discovery."""
from __future__ import annotations
from .base_provider import BaseLLMProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}

    def register(self, provider: BaseLLMProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> BaseLLMProvider | None:
        return self._providers.get(name)

    def list_all(self) -> list[dict]:
        return [p.status() for p in self._providers.values()]

    def get_enabled(self) -> list[str]:
        return [name for name, p in self._providers.items() if p.enabled]


# ── Singleton ─────────────────────────────────────────────

provider_registry = ProviderRegistry()
