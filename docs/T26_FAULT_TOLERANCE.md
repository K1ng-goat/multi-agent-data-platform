# T26 Agent Fault Tolerance

> **Date**: 2026-06-04  
> **Baseline**: T25 MemoryRouter  
> **Env Vars**: `MAX_AGENT_RETRY=2`, `AGENT_TIMEOUT_SECONDS=30`

---

## Architecture

```
BEFORE (T25)                          AFTER (T26)
─────────────                         ────────────
execute_pipeline:                     execute_pipeline:
  for each agent:                       for each agent:
    agent.execute()  → crash?            safe_execute(agent)
      ↓ pipeline dies                      ↓
                                         retry? timeout?
                                           ↓
                                         AgentExecutionResult
                                           ↓
                                         pipeline continues
```

## Retry Strategy

```
Attempt 1 → FAIL  (RuntimeError)
  wait 0ms
Attempt 2 → FAIL  (same error)
  wait 0ms
Attempt 3 → OK    → return success

MAX_AGENT_RETRY=2 means 2 retries (3 total attempts)
Set via: export MAX_AGENT_RETRY=2
```

## Timeout Strategy

```
agent.execute() starts
  ↓
asyncio.wait_for(execute, timeout=30s)
  ↓
  timeout?   → return AgentExecutionResult(success=False, error="timeout after 30s")
  exception? → retry? → yes: try again | no: return failure
  OK?        → return success
```

## AgentExecutionResult Schema

```python
@dataclass
class AgentExecutionResult:
    success: bool                 # did agent complete?
    agent: str                    # agent name
    data: dict                    # output context (empty on failure)
    error: str | None             # last error message
    retry_count: int              # number of retries
    duration_ms: float            # total execution time
```

## Partial Success Example

```json
{
  "agent_results": [
    {"agent": "DataAgent",   "success": true,  "duration_ms": 1200, "retry_count": 0},
    {"agent": "AuditAgent",  "success": false, "error": "RuntimeError: null check failed", "retry_count": 2},
    {"agent": "ChartAgent",  "success": true,  "duration_ms": 800,  "retry_count": 0},
    {"agent": "ReportAgent", "success": true,  "duration_ms": 3400, "retry_count": 0}
  ],
  "partial_success": true,
  "errors": ["Partial success: 1 agent(s) failed — ['AuditAgent']"]
}
```

## Verification

```
1. Success case:           0ms, retries=0           OK
2. Retry (fail→succeed):   2 calls, retries=1       OK
3. Total failure:          context preserved        OK
4. Timeout (1s):           elapsed=1.0s             OK
5. Result serializable:    5 keys                   OK
6. DataMasterAgent loads:  name=MasterAgent         OK
7. Routes:                 30                       OK
8. /analyze:               200                      OK
```

## Files

| File | Change |
|------|--------|
| `agents/recovery.py` | **NEW** — safe_execute, AgentExecutionResult (100 lines) |
| `agents/data_master_agent.py` | **MODIFIED** — execute_pipeline uses safe_execute |
| `docs/T26_FAULT_TOLERANCE.md` | Design document |
