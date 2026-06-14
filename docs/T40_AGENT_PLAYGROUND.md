# T40 Agent Playground

> **Date**: 2026-06-04  
> **Endpoint**: `POST /agent/run`  
> **Page**: `/playground`

---

## Architecture

```
Frontend /playground
  ↓
POST /agent/run {agent, prompt}
  ↓
AgentRegistry.get(agent)  (T27)
safe_execute()            (T26)
trace_store.save()        (T30)
evaluator.evaluate()      (T35)
  ↓
{output, duration_ms, score, trace_id}
```

## API

### POST /agent/run

```json
// Request
{"agent": "DataAgent", "prompt": "Analyze sales trends"}

// Response
{
  "agent": "DataAgent",
  "output": {...},
  "duration_ms": 0.0,
  "success": true,
  "score": 86.2,
  "trace_id": "f6f6617d20bf"
}
```

## Frontend Page

```
/playground
├── Agent selector (DataAgent, AuditAgent, ChartAgent, ReportAgent, StyleAgent)
├── Prompt textarea
├── Execute button
└── Result panel (agent, duration, score, success, output JSON, trace ID)
```

## Files

| File | Change |
|------|--------|
| `frontend/src/app/playground/page.tsx` | **NEW** — Playground UI |
| `main.py` | **MODIFIED** — +POST /agent/run |
| `docs/T40_AGENT_PLAYGROUND.md` | Design document |

## Verification

```
POST /agent/run:    200, score=86.2, trace_id returned
Unknown agent:      error with available list
Routes:             49
```
