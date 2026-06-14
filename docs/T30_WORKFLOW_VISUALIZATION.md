# T30 Workflow Visualization

> **Date**: 2026-06-04  
> **Baseline**: T29 Tool Registry  
> **Endpoints**: `GET /workflow/trace/{id}`, `GET /workflow/latest`

---

## Architecture

```
/analyze
  ↓
AgentOrchestrator.run_analysis_pipeline()
  ↓
trace = trace_store.start_trace(session_id)
  ↓
trace.add_step("ChartAgent", True, 89ms, "ChartTool")
trace.add_step("DataAgent", True, 234ms, "ExcelTool")
  ↓
trace_store.save(trace)
  ↓
GET /workflow/latest → trace.to_dict()
```

## Data Model

```python
WorkflowStep:
    step_id, agent_name, tool_name, duration_ms, success, error

WorkflowTrace:
    workflow_id, session_id, steps[]
    total_duration_ms, agent_count, success_rate, step_count
```

## API

### GET /workflow/latest

```json
{
  "workflow_id": "03cd1493db23",
  "session_id": "65d9f08dbe80",
  "total_duration_ms": 0.0,
  "agent_count": 2,
  "success_rate": 100.0,
  "step_count": 2,
  "steps": [
    {"step_id": "abc123", "agent_name": "ChartAgent", "tool_name": "ChartTool",
     "duration_ms": 89.0, "success": true, "error": null},
    {"step_id": "def456", "agent_name": "DataAgent", "tool_name": "ExcelTool",
     "duration_ms": 234.0, "success": true, "error": null}
  ]
}
```

### GET /workflow/trace/{workflow_id}

Same format as above, filtered by workflow_id.

## Files

| File | Change |
|------|--------|
| `workflow_trace.py` | **NEW** — WorkflowStep, WorkflowTrace, TraceStore (115 lines) |
| `agents/orchestrator.py` | **MODIFIED** — trace recording at each step |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T30_WORKFLOW_VISUALIZATION.md` | Design document |

## Verification

```
Trace structure:         3 steps, 3 agents, 100% success
store.save/get:          OK
to_dict():               7 keys
/analyze:                200, trace recorded
GET /workflow/latest:    step_count=2, agent_count=2
GET /workflow/trace/{id}:200
Routes:                  35 (30 + 2 metrics + 1 tools + 2 workflow)
Step durations:          all >= 0
```
