"""PlannerAgent — decides the analysis execution plan before orchestration.

Inspects dataset metadata and user intent to produce an AnalysisPlan
that tells the AgentOrchestrator which agents to run.  This replaces
the old "always run everything" approach with selective execution.

Extension points (future agents):
  - ForecastAgent    (time-series prediction)
  - AnomalyAgent     (statistical outlier detection)
  - RecommendationAgent (business suggestions)
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class AnalysisPlan:
    """Execution plan consumed by AgentOrchestrator.

    Each boolean flag controls whether the corresponding step runs.
    Additional fields (kpi_targets, chart_types, required_agents) provide hints.

    T27: required_agents is the canonical list of agent names to execute.
    Boolean flags are derived convenience for backward compat.
    """
    run_audit: bool = True
    run_kpi: bool = True
    run_charts: bool = True
    run_report: bool = True
    run_style: bool = False

    chart_types: list[str] = field(default_factory=lambda: ["line", "bar", "pie"])
    kpi_targets: list[str] = field(default_factory=list)
    required_agents: list[str] = field(default_factory=list)  # T27: registry keys

    def to_dict(self) -> dict:
        return asdict(self)


class PlannerAgent:
    """Inspects dataset metadata to produce an execution plan.

    Currently heuristic-based (no LLM call).  Future versions may use
    DeepSeek for complex planning decisions.
    """

    name = "PlannerAgent"
    description = "Planner — inspects data + intent, decides execution plan"

    def plan(self, data_summary: dict, user_intent: str = "analyze") -> AnalysisPlan:
        """Produce an AnalysisPlan from dataset metadata.

        Args:
            data_summary: The built summary dict {filename, shape, columns, dtypes, describe, ...}
            user_intent: From the intent classifier (analyze, full_report, audit, chart, etc.)

        Returns:
            AnalysisPlan with boolean flags for each pipeline step.
        """
        plan = AnalysisPlan()
        columns = data_summary.get("columns", [])
        shape = data_summary.get("shape", {})
        row_count = shape.get("rows", 0)
        col_count = shape.get("columns", 0)
        dtypes = data_summary.get("dtypes", {})
        null_counts = data_summary.get("null_counts", {})

        # ── Audit: always useful if there are columns to check ──
        plan.run_audit = col_count > 0

        # ── KPI (AI analysis): requires numeric columns ──
        numeric_cols = [c for c, t in dtypes.items()
                        if any(kw in str(t).lower() for kw in ("int", "float", "number"))]
        plan.run_kpi = len(numeric_cols) > 0

        # ── Charts: requires 2+ rows and at least 1 numeric column ──
        plan.run_charts = row_count >= 2 and len(numeric_cols) > 0

        # ── Report: enabled when AI analysis is on ──
        plan.run_report = plan.run_kpi

        # ── Chart type hints based on data shape ──
        if row_count <= 10 and len(numeric_cols) >= 1:
            plan.chart_types = ["bar", "pie"]  # small dataset → bar + pie
        if row_count > 10:
            plan.chart_types = ["line", "bar", "pie"]  # more data → include trend

        # ── KPI targets: auto-detect the best numeric columns ──
        plan.kpi_targets = numeric_cols[:3]

        # ── Intent overrides ──
        if user_intent == "audit":
            plan.run_kpi = False
            plan.run_charts = False
            plan.run_report = False
        elif user_intent == "chart":
            plan.run_audit = False
            plan.run_kpi = False
            plan.run_report = False
        elif user_intent == "full_report":
            plan.run_audit = True
            plan.run_kpi = True
            plan.run_charts = True
            plan.run_report = True

        # ── Data quality hints ──
        total_nulls = sum(int(v) for v in null_counts.values())
        if total_nulls > 0:
            plan.run_audit = True  # always audit when nulls present

        # ── T27: derive required_agents from boolean flags ──
        plan.required_agents = []
        if plan.run_audit:
            plan.required_agents.append("AuditAgent")
        if plan.run_kpi:
            plan.required_agents.append("DataAgent")
        if plan.run_charts:
            plan.required_agents.append("ChartAgent")
        if plan.run_report:
            plan.required_agents.append("ReportAgent")
        if plan.run_style:
            plan.required_agents.append("StyleAgent")

        print(f"[Planner] plan: audit={plan.run_audit} kpi={plan.run_kpi} "
              f"charts={plan.run_charts} report={plan.run_report} "
              f"agents={plan.required_agents}")

        return plan

    def add_step(self, context: dict, status: str, message: str):
        context.setdefault("steps", []).append({
            "agent": self.name,
            "status": status,
            "message": message,
        })
