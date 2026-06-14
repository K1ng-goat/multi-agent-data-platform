"""Agent Fault Tolerance — graceful degradation for agent pipelines.

Provides safe_execute() which wraps any agent call with:
  - Retry (MAX_AGENT_RETRY)
  - Timeout (AGENT_TIMEOUT_SECONDS)
  - Execution metrics (duration, retry_count)
  - Structured result (AgentExecutionResult)

If an agent fails after all retries, the pipeline continues with the
previous context — one agent failure does not stop the whole pipeline.
"""
from __future__ import annotations
import os
import time
import asyncio
import traceback
from dataclasses import dataclass, field


@dataclass
class AgentExecutionResult:
    """Structured result from a single agent execution."""
    success: bool
    agent: str
    data: dict = field(default_factory=dict)    # agent output context
    error: str | None = None                     # last error message
    retry_count: int = 0                         # number of retries attempted
    duration_ms: float = 0.0                     # total execution time


# ── Configuration ──────────────────────────────────────────

def _max_retries() -> int:
    return int(os.getenv("MAX_AGENT_RETRY", "2"))


def _timeout_seconds() -> float:
    return float(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))


# ── Public API ─────────────────────────────────────────────

async def safe_execute(
    agent_name: str,
    execute_fn,   # async callable(context) → context
    context: dict,
) -> tuple[AgentExecutionResult, dict]:
    """Execute an agent with retry + timeout, returning structured result.

    If the agent fails after all retries, returns:
      - result.success = False
      - context unchanged (previous context is preserved)

    The caller can check ``result.success`` to decide whether to use
    or discard the output.
    """
    max_retry = _max_retries()
    timeout = _timeout_seconds()
    start = time.time()
    last_error = None
    retries = 0

    for attempt in range(max_retry + 1):
        if attempt > 0:
            retries = attempt
            print(f"[Recovery] {agent_name} retry {attempt}/{max_retry}")

        try:
            result_context = await asyncio.wait_for(
                execute_fn(context),
                timeout=timeout,
            )
            elapsed = (time.time() - start) * 1000
            print(f"[Recovery] {agent_name} OK — {elapsed:.0f}ms")
            result = AgentExecutionResult(
                success=True,
                agent=agent_name,
                data=result_context,
                retry_count=retries,
                duration_ms=elapsed,
            )
            _record_metrics(result)  # T28
            return result, result_context

        except asyncio.TimeoutError:
            last_error = f"timeout after {timeout}s"
            print(f"[Recovery] {agent_name} timeout ({timeout}s)")
        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:120]}"
            print(f"[Recovery] {agent_name} error: {last_error}")
            traceback.print_exc()

    # All attempts exhausted
    elapsed = (time.time() - start) * 1000
    result = AgentExecutionResult(
        success=False,
        agent=agent_name,
        error=last_error,
        retry_count=retries,
        duration_ms=elapsed,
    )
    _record_metrics(result)  # T28
    return result, context  # return unchanged context


def _record_metrics(result: AgentExecutionResult) -> None:
    """T28: Record execution result into the metrics registry."""
    try:
        from .metrics import metrics_registry
        metrics_registry.record(
            agent_name=result.agent,
            success=result.success,
            duration_ms=result.duration_ms,
            retry_count=result.retry_count,
        )
    except Exception:
        pass  # metrics recording must never break the pipeline
