# T28 Agent Observability

> **Date**: 2026-06-04  
> **Baseline**: T27 Dynamic Registry  
> **Endpoints**: `GET /agent/metrics`, `POST /agent/metrics/reset`

---

## Architecture

```
safe_execute(agent, ctx)
  ↓
result = AgentExecutionResult(...)
  ↓
_record_metrics(result)          ← T28: auto-record
  ↓
metrics_registry.record(name, success, duration, retries)
```

## AgentMetrics Model

```python
@dataclass
class AgentMetrics:
    agent_name: str
    runs: int                    # total executions
    success_count: int           # successful executions
    failure_count: int           # failed executions
    total_duration_ms: float     # cumulative time
    total_retries: int           # cumulative retries

    @property
    def success_rate(self) -> float:     # 0-100%
    @property
    def avg_duration_ms(self) -> float:  # mean execution time
```

## API

### GET /agent/metrics

```json
{
  "metrics": {
    "DataAgent": {
      "agent_name": "DataAgent",
      "runs": 15,
      "success_count": 14,
      "failure_count": 1,
      "success_rate": 93.3,
      "avg_duration_ms": 1200.5,
      "total_duration_ms": 18007.5,
      "total_retries": 2
    }
  }
}
```

### POST /agent/metrics/reset

```json
{"ok": true, "message": "Agent metrics reset"}
```

## Collection Flow

```
safe_execute() called
  ↓
result = AgentExecutionResult(success, agent, duration_ms, retry_count)
  ↓
_record_metrics(result)
  → metrics_registry.record(agent_name, success, duration_ms, retry_count)
  → thread-safe increment
```

Metrics recording is fire-and-forget — never blocks or breaks the pipeline.

## Files

| File | Change |
|------|--------|
| `agents/metrics.py` | **NEW** — AgentMetrics + MetricsRegistry (90 lines) |
| `agents/recovery.py` | **MODIFIED** — auto-record in safe_execute |
| `main.py` | **MODIFIED** — +2 endpoints, +1 import |
| `docs/T28_AGENT_OBSERVABILITY.md` | Design document |

## Verification

```
MetricsRegistry:     empty start
record():             runs=3 success_rate=66.7% avg=300ms
get_all():            keys returned
reset():              cleared
Auto-record:          OkAgent=1, FailAgent=1
Routes:               32 (30 + 2 metrics)
GET /agent/metrics:   200
POST reset:           cleared confirmed
Batch:                5 runs, avg calculated
```
