"""Workflow Trace — execution visualization for agent pipelines.

Records each agent execution step with timing, then exposes traces
via GET /workflow/trace/{id} and GET /workflow/latest.
"""
from __future__ import annotations
import time
import uuid
import threading
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    step_id: str = ""
    agent_name: str = ""
    tool_name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "error": self.error,
        }


@dataclass
class WorkflowTrace:
    workflow_id: str = ""
    session_id: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)

    @property
    def total_duration_ms(self) -> float:
        if not self.steps:
            return 0.0
        return round(max(s.end_time for s in self.steps) -
                     min(s.start_time for s in self.steps), 1)

    @property
    def agent_count(self) -> int:
        return len({s.agent_name for s in self.steps})

    @property
    def success_rate(self) -> float:
        if not self.steps:
            return 100.0
        ok = sum(1 for s in self.steps if s.success)
        return round(ok / len(self.steps) * 100, 1)

    def add_step(self, agent_name: str, success: bool,
                 duration_ms: float = 0.0, tool_name: str = "",
                 error: str | None = None) -> WorkflowStep:
        now = time.time()
        step = WorkflowStep(
            step_id=uuid.uuid4().hex[:8],
            agent_name=agent_name,
            tool_name=tool_name,
            start_time=now - duration_ms / 1000.0,
            end_time=now,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )
        self.steps.append(step)
        return step

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "total_duration_ms": self.total_duration_ms,
            "agent_count": self.agent_count,
            "success_rate": self.success_rate,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
        }


class TraceStore:
    """In-memory store for workflow traces (latest + by ID)."""

    def __init__(self):
        self._traces: dict[str, WorkflowTrace] = {}
        self._latest: WorkflowTrace | None = None
        self._lock = threading.Lock()

    def save(self, trace: WorkflowTrace) -> None:
        with self._lock:
            self._traces[trace.workflow_id] = trace
            self._latest = trace
            # Cap at 100 traces
            if len(self._traces) > 100:
                oldest = next(iter(self._traces))
                del self._traces[oldest]

    def get(self, workflow_id: str) -> WorkflowTrace | None:
        return self._traces.get(workflow_id)

    def get_latest(self) -> WorkflowTrace | None:
        return self._latest

    def start_trace(self, session_id: str) -> WorkflowTrace:
        """Create a new trace entry."""
        trace = WorkflowTrace(
            workflow_id=uuid.uuid4().hex[:12],
            session_id=session_id,
        )
        return trace


# ── Singleton ─────────────────────────────────────────────

trace_store = TraceStore()
