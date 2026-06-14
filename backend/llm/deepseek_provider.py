"""DeepSeekProvider — wraps existing DeepSeek API calls.

Preserves all existing behavior: same endpoint, same model, same headers.
This is a thin wrapper — the actual HTTP calls are unchanged.
"""
from __future__ import annotations
import os
import httpx
from .base_provider import BaseLLMProvider
from cost_tracker import cost_tracker  # T44

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DeepSeekProvider(BaseLLMProvider):
    name = "deepseek"
    enabled = True

    async def generate(self, prompt: str, **kwargs) -> str:
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        temperature = kwargs.get("temperature", 0.7)
        tools = kwargs.get("tools")
        api_key = kwargs.get("api_key") or os.getenv("DEEPSEEK_API_KEY", "")

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def chat_completion(self, **kwargs) -> dict:
        """Full chat completion with tool support. Returns raw API response."""
        messages = kwargs.get("messages", [])
        temperature = kwargs.get("temperature", 0.7)
        tools = kwargs.get("tools")
        api_key = kwargs.get("api_key") or os.getenv("DEEPSEEK_API_KEY", "")
        payload = {"model": "deepseek-chat", "messages": messages, "temperature": temperature}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # T44: Track cost
            usage = data.get("usage", {})
            if usage:
                cost_tracker.record(
                    "deepseek-chat", "api",
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                )
            return data