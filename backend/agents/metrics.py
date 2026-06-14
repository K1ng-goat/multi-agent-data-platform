"""Agent Observability — runtime metrics collection for all registered agents.

Tracks per-agent: runs, successes, failures, duration, retries.
Exposed via GET /agent/metrics and reset via POST /agent/metrics/reset.
"""
from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field


@dataclass
class AgentMetrics:
    """Per-agent execution metrics."""
    agent_name: str = ""
    runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    total_retries: int = 0

    @property
    def success_rate(self) -> float:
        if self.runs == 0:
            return 100.0
        return round(self.success_count / self.runs * 100, 1)

    @property
    def avg_duration_ms(self) -> float:
        if self.runs == 0:
            return 0.0
        return round(self.total_duration_ms / self.runs, 1)

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "runs": self.runs,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "total_retries": self.total_retries,
        }


class MetricsRegistry:
    """Thread-safe registry for agent metrics."""

    def __init__(self):
        self._metrics: dict[str, AgentMetrics] = {}
        self._lock = threading.Lock()

    def record(self, agent_name: str, success: bool,
               duration_ms: float, retry_count: int = 0) -> None:
        """Record a single agent execution."""
        with self._lock:
            if agent_name not in self._metrics:
                self._metrics[agent_name] = AgentMetrics(agent_name=agent_name)
            m = self._metrics[agent_name]
            m.runs += 1
            if success:
                m.success_count += 1
            else:
                m.failure_count += 1
            m.total_duration_ms += duration_ms
            m.total_retries += retry_count

    def get(self, agent_name: str) -> AgentMetrics | None:
        with self._lock:
            return self._metrics.get(agent_name)

    def get_all(self) -> dict[str, dict]:
        with self._lock:
            return {name: m.to_dict() for name, m in self._metrics.items()}

    def reset(self) -> None:
        with self._lock:
            self._metrics.clear()

    def __len__(self) -> int:
        return len(self._metrics)


# ── Singleton ─────────────────────────────────────────────

metrics_registry = MetricsRegistry()
