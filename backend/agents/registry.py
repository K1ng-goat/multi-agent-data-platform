"""Dynamic Agent Registry — plugin-style agent discovery and instantiation.

Replaces hard-coded AGENT_CLASSES dict and INTENT_AGENT_MAP with a
register-on-import pattern.  Any new agent just calls registry.register().

Usage:
  from agents.registry import registry
  from agents.audit_agent import AuditAgent
  registry.register("audit", AuditAgent)
"""
from __future__ import annotations
from .base_agent import BaseAgent


class AgentRegistry:
    """Central registry for agent classes.

    Agents register themselves at module import time.  The orchestrator
    and planner query the registry dynamically — no hard-coded class
    references outside this module.
    """

    def __init__(self):
        self._classes: dict[str, type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}  # lazy singleton cache

    def register(self, name: str, cls: type[BaseAgent]) -> None:
        """Register an agent class by name."""
        self._classes[name] = cls
        print(f"[Registry] registered: {name}")

    def get(self, name: str) -> BaseAgent:
        """Get or create a singleton agent instance by name."""
        if name not in self._instances:
            if name not in self._classes:
                raise KeyError(f"Agent '{name}' not registered. Known: {list(self._classes.keys())}")
            self._instances[name] = self._classes[name]()
        return self._instances[name]

    def list_agents(self) -> list[str]:
        """Return all registered agent names."""
        return sorted(self._classes.keys())

    def get_intent_agents(self, intent: str) -> list[str]:
        """Map an intent string to a list of agent names.

        This replaces the old INTENT_AGENT_MAP hard-coded dict.
        """
        mapping = {
            "analyze":            ["DataAgent"],
            "chart":              ["ChartAgent"],
            "audit":              ["AuditAgent"],
            "report":             ["ReportAgent"],
            "style":              ["StyleAgent"],
            "export":             ["ExportAgent"],
            "full_report":        ["DataAgent", "AuditAgent", "ChartAgent",
                                   "ReportAgent", "StyleAgent", "ExportAgent"],
            "data_with_charts":   ["DataAgent", "ChartAgent"],
            "analyze_and_report": ["DataAgent", "ReportAgent"],
        }
        return mapping.get(intent, ["DataAgent"])

    def __len__(self) -> int:
        return len(self._classes)


# ── Singleton ─────────────────────────────────────────────

registry = AgentRegistry()
