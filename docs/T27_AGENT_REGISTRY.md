# T27 Dynamic Agent Registry

> **Date**: 2026-06-04
> **Baseline**: T26 Fault Tolerance
> **Goal**: Replace hard-coded agent instantiation with registry-driven execution

---

## Architecture

```
BEFORE (T26)                          AFTER (T27)
─────────────                         ────────────
AGENT_CLASSES = {                     registry.register("DataAgent", DataAgent)
    "DataAgent": DataAgent,           registry.register("AuditAgent", AuditAgent)
    "AuditAgent": AuditAgent,         ...
    ...                               registry.get_intent_agents("full_report")
}                                     → ["DataAgent", "AuditAgent", ...]
INTENT_AGENT_MAP = {
    "full_report": ["DataAgent", ...]
}
```

## Registration Flow

```
Module import
  ↓
agent file (e.g., audit_agent.py)
  ↓
from .registry import registry
registry.register("AuditAgent", AuditAgent)
  ↓
Registry._classes["AuditAgent"] = AuditAgent
```

## Dynamic Execution Flow

```
Intent "full_report"
  ↓
registry.get_intent_agents("full_report")
  → ["DataAgent", "AuditAgent", "ChartAgent", "ReportAgent", "StyleAgent", "ExportAgent"]
  ↓
for name in agents:
    agent = registry.get(name)       ← lazy singleton
    result = safe_execute(name, agent.execute, ctx)
```

## Registered Agents

```
AuditAgent    — data quality check
ChartAgent    — chart generation
DataAgent     — statistical + AI analysis
ExportAgent   — file export
ReportAgent   — markdown report
StyleAgent    — theme/style
```

## Files

| File | Change |
|------|--------|
| `agents/registry.py` | **NEW** — AgentRegistry class (70 lines) |
| `agents/data_master_agent.py` | **MODIFIED** — uses registry, not hard-coded dicts |
| `agents/planner_agent.py` | **MODIFIED** — AnalysisPlan.required_agents |
| `agents/{6 files}` | **MODIFIED** — +3 lines registry.register() each |

## Verification

```
list_agents():   6 agents registered
registry.get():  all instantiable
get_intent_agents: analyze=1, full_report=6, chart=1
Planner required_agents: [AuditAgent, DataAgent, ChartAgent, ReportAgent]
plan_tasks:       registry-driven
Routes:           30
/analyze:         200
```

## Extending (New Agent)

```python
# 1. Create agents/forecast_agent.py
class ForecastAgent(BaseAgent):
    name = "ForecastAgent"
    description = "Time-series forecasting"

from .registry import registry
registry.register("ForecastAgent", ForecastAgent)

# 2. Add to registry.get_intent_agents()
"forecast": ["ForecastAgent"]

# 3. Add to Planner heuristic
if has_date_column:
    plan.required_agents.append("ForecastAgent")
```
