"""CostTracker — tracks LLM token usage and estimated cost.

DeepSeek pricing (approximate, USD):
  deepseek-chat:  input $0.14/M, output $0.28/M
"""
from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field


# Price per 1M tokens (USD)
PRICING = {"deepseek-chat": {"input": 0.14, "output": 0.28}}


@dataclass
class CostEntry:
    model: str = "deepseek-chat"
    agent: str = "unknown"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def estimated_cost(self) -> float:
        price = PRICING.get(self.model, {"input": 0.14, "output": 0.28})
        return round(
            self.prompt_tokens / 1_000_000 * price["input"] +
            self.completion_tokens / 1_000_000 * price["output"], 6
        )

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "agent": self.agent,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": self.estimated_cost,
            "timestamp": self.timestamp,
        }


class CostTracker:
    def __init__(self):
        self._entries: list[CostEntry] = []
        self._lock = threading.Lock()

    def record(self, model: str, agent: str, prompt_tokens: int,
               completion_tokens: int) -> CostEntry:
        entry = CostEntry(
            model=model, agent=agent,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            timestamp=time.time(),
        )
        with self._lock:
            self._entries.append(entry)
        print(f"[CostTracker] {agent}: {entry.total_tokens} tokens, \${entry.estimated_cost:.6f}")
        return entry

    def get_all(self) -> list[dict]:
        with self._lock:
            return [e.to_dict() for e in self._entries[-100:]]

    def get_summary(self) -> dict:
        with self._lock:
            if not self._entries:
                return {"total_tokens": 0, "total_cost": 0, "calls": 0}
            total_tokens = sum(e.total_tokens for e in self._entries)
            total_cost = sum(e.estimated_cost for e in self._entries)
            by_agent: dict[str, dict] = {}
            for e in self._entries:
                if e.agent not in by_agent:
                    by_agent[e.agent] = {"tokens": 0, "cost": 0, "calls": 0}
                by_agent[e.agent]["tokens"] += e.total_tokens
                by_agent[e.agent]["cost"] += e.estimated_cost
                by_agent[e.agent]["calls"] += 1
            for v in by_agent.values():
                v["cost"] = round(v["cost"], 6)
            return {
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 6),
                "calls": len(self._entries),
                "by_agent": by_agent,
            }

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()


# ── Singleton ─────────────────────────────────────────────

cost_tracker = CostTracker()
