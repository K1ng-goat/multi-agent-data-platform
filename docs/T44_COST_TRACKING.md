# T44 LLM Cost Tracking

> **Date**: 2026-06-04  
> **Endpoints**: `GET /costs`, `GET /costs/summary`

---

## Architecture

```
DeepSeek API Response
  ↓
usage: {prompt_tokens, completion_tokens}
  ↓
cost_tracker.record(model, agent, prompt_tokens, completion_tokens)
  ↓
CostEntry {total_tokens, estimated_cost}
  ↓
GET /costs + GET /costs/summary
```

## Pricing (DeepSeek)

```
deepseek-chat:  input $0.14/M,  output $0.28/M
```

## CostEntry

```python
model, agent, prompt_tokens, completion_tokens, total_tokens,
estimated_cost, timestamp
```

## API

```
GET /costs          → 100 most recent entries
GET /costs/summary  → {total_tokens, total_cost, calls, by_agent}
```

## Example Summary

```json
{
  "total_tokens": 5100,
  "total_cost": 0.000938,
  "calls": 3,
  "by_agent": {
    "DataAgent": {"tokens": 2300, "cost": 0.000434, "calls": 2},
    "ReportAgent": {"tokens": 2800, "cost": 0.000504, "calls": 1}
  }
}
```

## Files

| File | Change |
|------|--------|
| `cost_tracker.py` | **NEW** — CostTracker (85 lines) |
| `llm/deepseek_provider.py` | **MODIFIED** — auto-track after API calls |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T44_COST_TRACKING.md` | Design document |

## Verification

```
Entry:     tokens=1500 cost=$0.00028
Summary:   calls=3 tokens=5100 cost=$0.000938 by_agent=[DataAgent,ReportAgent]
API:       200 (both endpoints)
Routes:    55
```