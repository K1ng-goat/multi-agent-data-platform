# T33 Dynamic Agent Plugin System

> **Date**: 2026-06-04  
> **Endpoint**: `GET /agents`

---

## Architecture

```
Startup
  ↓
PluginLoader.load_plugins()
  ↓
Scan agents/*.py + agents/plugins/*.py
  ↓
Find BaseAgent subclasses
  ↓
registry.register(name, cls)
  ↓
7 agents available
```

## Plugin Discovery

```
agents/
├── data_agent.py        → DataAgent      (auto-discovered)
├── chart_agent.py       → ChartAgent     (auto-discovered)
├── audit_agent.py       → AuditAgent     (auto-discovered)
├── report_agent.py      → ReportAgent    (auto-discovered)
├── style_agent.py       → StyleAgent     (auto-discovered)
├── export_agent.py      → ExportAgent    (auto-discovered)
├── data_master_agent.py → MasterAgent    (auto-discovered)
└── plugins/                              ← drop-in directory
    └── new_agent.py     → NewAgent       (auto-discovered)
```

## Adding a Plugin

```python
# agents/plugins/forecast_agent.py
from agents.base_agent import BaseAgent
from agents.registry import registry

class ForecastAgent(BaseAgent):
    name = "ForecastAgent"
    description = "Time-series forecasting"

    async def execute(self, context):
        # ... forecasting logic
        return context

registry.register("ForecastAgent", ForecastAgent)
```

No config changes needed. PluginLoader discovers it automatically.

## Files

| File | Change |
|------|--------|
| `agents/plugin_loader.py` | **NEW** — auto-discovery (75 lines) |
| `agents/plugins/__init__.py` | **NEW** — plugin directory |
| `main.py` | **MODIFIED** — +GET /agents endpoint |
| `docs/T33_PLUGIN_SYSTEM.md` | Design document |

## Verification

```
PluginLoader:       7 agents auto-discovered
GET /agents:        200, 7 agents
Idempotent:         re-run loads 0 new
Routes:             36
/analyze:           200
/chat:              200
All have execute():  OK
```
