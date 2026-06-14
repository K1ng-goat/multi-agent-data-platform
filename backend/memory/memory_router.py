"""MemoryRouter — decides which memory layers to retrieve for a given plan.

Sits between PlannerAgent and AgentOrchestrator.  The router reads the
execution plan and user intent, then selectively queries only the memory
layers that are relevant — avoiding unnecessary DB/disk I/O.

Feature flag:
  ENABLE_MEMORY_ROUTER=true   → router active
  (default/unset)             → router bypassed (backward compat)
"""
from __future__ import annotations
import os
import traceback
from dataclasses import dataclass, field, asdict
from memory.memory_manager import get_memory_manager


@dataclass
class MemoryContext:
    """Assembled memory context consumed by AgentOrchestrator."""

    user_preferences: dict = field(default_factory=dict)
    workspace_context: dict | None = None
    conversation_summary: str = ""
    analysis_history: list[dict] = field(default_factory=list)

    # Metadata
    layers_queried: list[str] = field(default_factory=list)
    total_keys: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_empty(self) -> bool:
        return self.total_keys == 0


class MemoryRouter:
    """Routes memory retrieval based on execution plan + user intent.

    Decision matrix:
      - KPI analysis    → user_preferences + analysis_history
      - Audit           → workspace_context
      - Charts          → workspace_context (for chart config reuse)
      - Report          → user_preferences + conversation_summary + analysis_history
      - Style           → user_preferences
    """

    name = "MemoryRouter"
    description = "Memory router — selective memory retrieval based on execution plan"

    def route(
        self,
        user_id: int,
        session_id: str = "",
        plan=None,          # AnalysisPlan
        user_intent: str = "analyze",
    ) -> MemoryContext:
        """Decide which memory layers to query and assemble a MemoryContext.

        Returns an empty MemoryContext if the feature flag is not set.
        """
        if not _is_enabled():
            return MemoryContext()

        ctx = MemoryContext()
        mgr = get_memory_manager()

        # ── Always retrieve user preferences (lightweight) ──
        try:
            ctx.user_preferences = mgr.get_user_preferences(user_id)
            ctx.layers_queried.append("user_preferences")
            ctx.total_keys += len(ctx.user_preferences)
        except Exception:
            print("[MemoryRouter] ERROR user_preferences:")
            traceback.print_exc()

        # ── Determine what else to fetch based on plan/intent ──
        needs_kpi = _needs(plan, "run_kpi") or user_intent in ("analyze", "full_report", "analyze_and_report")
        needs_audit = _needs(plan, "run_audit") or user_intent == "audit"
        needs_charts = _needs(plan, "run_charts") or user_intent == "chart"
        needs_report = _needs(plan, "run_report") or user_intent in ("full_report", "analyze_and_report")

        # ── Workspace context: needed for audit + charts (data knowledge) ──
        if session_id and (needs_audit or needs_charts):
            try:
                ws = mgr.get_workspaces(user_id, limit=1)
                if ws:
                    ctx.workspace_context = ws[0]
                    ctx.layers_queried.append("workspace")
            except Exception:
                print("[MemoryRouter] ERROR workspace:")
                traceback.print_exc()

        # ── Analysis history: needed for KPI + report (trend awareness) ──
        if needs_kpi or needs_report:
            try:
                ctx.analysis_history = mgr.get_recent_analyses(user_id, limit=3)
                ctx.layers_queried.append("analysis_history")
                ctx.total_keys += len(ctx.analysis_history)
            except Exception:
                print("[MemoryRouter] ERROR analysis_history:")
                traceback.print_exc()

        # ── Conversation summary: needed for report (context continuity) ──
        if session_id and needs_report:
            try:
                convos = mgr.get_conversation_history(user_id, session_id, limit=5)
                if convos:
                    parts = [c.get("content", "")[:80] for c in convos if c.get("content")]
                    ctx.conversation_summary = " | ".join(parts[-3:])
                    ctx.layers_queried.append("conversation")
            except Exception:
                print("[MemoryRouter] ERROR conversation:")
                traceback.print_exc()

        print(f"[MemoryRouter] plan: kpi={needs_kpi} audit={needs_audit} "
              f"charts={needs_charts} report={needs_report} "
              f"→ layers={ctx.layers_queried} keys={ctx.total_keys}")

        return ctx


# ── Internal helpers ──────────────────────────────────────

def _is_enabled() -> bool:
    return os.getenv("ENABLE_MEMORY_ROUTER", "").lower() in ("true", "1", "yes")


def _needs(plan, key: str) -> bool:
    """Check whether a plan flag is True.  None plan = don't know = False."""
    if plan is None:
        return False
    return bool(getattr(plan, key, False))
