"""BaseLLMProvider — abstract interface for all LLM providers."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    name: str = "base"
    enabled: bool = False

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        ...

    def status(self) -> dict:
        return {"id": self.name, "enabled": self.enabled}
