"""WorkflowDefinition — reusable workflow templates for agent execution.

Provides 5 predefined workflows that map directly to agent registry names.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class WorkflowDefinition:
    name: str = ""
    description: str = ""
    agents: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    category: str = "general"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "agents": self.agents,
            "tools": self.tools,
            "category": self.category,
        }


# ── Predefined Workflow Templates ─────────────────────────

WORKFLOW_TEMPLATES: dict[str, WorkflowDefinition] = {
    "financial_analysis": WorkflowDefinition(
        name="financial_analysis",
        description="Complete financial data analysis with audit and report",
        agents=["DataAgent", "AuditAgent", "ChartAgent", "ReportAgent"],
        tools=["ExcelTool", "ChartTool", "MemoryTool"],
        category="finance",
    ),
    "quality_audit": WorkflowDefinition(
        name="quality_audit",
        description="Data quality audit — nulls, duplicates, outliers",
        agents=["DataAgent", "AuditAgent"],
        tools=["ExcelTool"],
        category="quality",
    ),
    "chart_dashboard": WorkflowDefinition(
        name="chart_dashboard",
        description="Generate charts and dashboard KPIs from data",
        agents=["DataAgent", "ChartAgent"],
        tools=["ExcelTool", "ChartTool"],
        category="visualization",
    ),
    "full_report": WorkflowDefinition(
        name="full_report",
        description="End-to-end: analysis, audit, charts, report, style, export",
        agents=["DataAgent", "AuditAgent", "ChartAgent", "ReportAgent", "StyleAgent", "ExportAgent"],
        tools=["ExcelTool", "ChartTool", "ExportTool", "MemoryTool", "ThemeTool"],
        category="report",
    ),
    "quick_summary": WorkflowDefinition(
        name="quick_summary",
        description="Fast data overview — analysis only",
        agents=["DataAgent"],
        tools=["ExcelTool"],
        category="general",
    ),
}


class WorkflowLibrary:
    """Registry of predefined workflow templates."""

    def list_all(self) -> list[dict]:
        return [wf.to_dict() for wf in WORKFLOW_TEMPLATES.values()]

    def get(self, name: str) -> WorkflowDefinition | None:
        return WORKFLOW_TEMPLATES.get(name)

    def list_names(self) -> list[str]:
        return sorted(WORKFLOW_TEMPLATES.keys())

    def run(self, name: str, context: dict) -> dict:
        """Execute a workflow template against a context.

        Returns the workflow definition + execution metadata.
        The actual agent execution is handled by the caller (orchestrator).
        """
        wf = WORKFLOW_TEMPLATES.get(name)
        if not wf:
            return {"ok": False, "error": f"Workflow '{name}' not found"}

        return {
            "ok": True,
            "workflow": wf.to_dict(),
            "status": "ready",
        }


# ── Singleton ─────────────────────────────────────────────

workflow_library = WorkflowLibrary()
