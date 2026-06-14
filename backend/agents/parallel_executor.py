"""ParallelExecutionManager — concurrent agent group execution.

Replaces the sequential for-loop in execute_pipeline with dependency-aware
parallel execution via asyncio.gather().

Dependency model (full_report intent):
  Group 1: [DataAgent]
  Group 2: [AuditAgent, ChartAgent]     ← parallel (both read DataAgent output)
  Group 3: [ReportAgent]                ← waits for Audit + Chart
  Group 4: [StyleAgent, ExportAgent]    ← parallel (both read ReportAgent output)
"""
from __future__ import annotations
import asyncio
import time
from .base_agent import BaseAgent
from .recovery import safe_execute


# ── Dependency graph ──────────────────────────────────────

PARALLEL_GROUPS: dict[str, list[list[str]]] = {
    # Each list is one parallel group. Groups execute sequentially.
    "full_report": [
        ["DataAgent"],
        ["AuditAgent", "ChartAgent"],
        ["ReportAgent"],
        ["StyleAgent", "ExportAgent"],
    ],
    "analyze_and_report": [
        ["DataAgent"],
        ["ReportAgent"],
    ],
    "data_with_charts": [
        ["DataAgent", "ChartAgent"],
    ],
    # Single-agent intents: no parallelism needed
    "analyze":  [["DataAgent"]],
    "chart":    [["ChartAgent"]],
    "audit":    [["AuditAgent"]],
    "report":   [["ReportAgent"]],
    "style":    [["StyleAgent"]],
    "export":   [["ExportAgent"]],
}


class ParallelExecutionManager:
    """Executes agent groups in sequence, with agents within a group running concurrently."""

    def __init__(self, get_agent_fn):
        self._get_agent = get_agent_fn

    async def execute(
        self,
        agent_names: list[str],
        context: dict,
    ) -> tuple[dict, list[dict]]:
        """Execute agents using the parallel group schedule.

        If the intent is not in PARALLEL_GROUPS, falls back to sequential
        execution of the provided agent_names list.

        Returns (context, execution_results).
        """
        intent = context.get("intent", "")
        groups = PARALLEL_GROUPS.get(intent)
        if groups is None:
            # Fallback: sequential execution
            groups = [[name] for name in agent_names]

        all_results: list[dict] = []

        for group in groups:
            # Filter to agents that are actually in the task list
            active = [name for name in group if name in agent_names]
            if not active:
                continue

            t0 = time.time()
            if len(active) == 1:
                # Single agent — run directly
                name = active[0]
                agent = self._get_agent(name)
                result, context = await safe_execute(name, agent.execute, context)
                all_results.append({
                    "agent": result.agent, "success": result.success,
                    "duration_ms": round(result.duration_ms, 1),
                    "retry_count": result.retry_count, "error": result.error,
                })
            else:
                # Multiple agents — run in parallel
                # Each gets its own copy of context to avoid race conditions
                tasks = []
                for name in active:
                    agent = self._get_agent(name)
                    ctx_copy = dict(context)  # shallow copy for safety
                    tasks.append(safe_execute(name, agent.execute, ctx_copy))

                parallel_results = await asyncio.gather(*tasks, return_exceptions=False)

                # Merge: use last successful context for each key
                for result, _ in parallel_results:
                    all_results.append({
                        "agent": result.agent, "success": result.success,
                        "duration_ms": round(result.duration_ms, 1),
                        "retry_count": result.retry_count, "error": result.error,
                    })
                    if result.success and result.data:
                        context.update(result.data)

            elapsed = (time.time() - t0) * 1000
            names = [r["agent"] for r in all_results[-len(active):]]
            print(f"[ParallelExecutor] group {names} — {elapsed:.0f}ms")

        return context, all_results
