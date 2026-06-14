# T35 Agent Evaluation Framework

> **Date**: 2026-06-04  
> **Endpoint**: `GET /agent/evaluation`

---

## Architecture

```
Agent Output
  ↓
AgentEvaluator.evaluate(agent_name, output, context)
  ↓
EvaluationResult {
  completeness, consistency, readability, relevance → final_score
}
  ↓
Aggregated in /agent/evaluation
```

## Scoring Dimensions

```
completeness   — non-empty output ratio      (0-100)
consistency    — structured keys ratio       (0-100)
readability    — string value length         (0-100)
relevance      — intent match in output      (60-100)
────────────────────────────────────────────────────
final_score    — average of 4 dimensions
```

## API

### GET /agent/evaluation

```json
{
  "evaluations": {
    "DataAgent": {
      "agent_name": "DataAgent",
      "runs": 3,
      "avg_score": 82.5,
      "min_score": 80.0,
      "max_score": 85.0
    }
  }
}
```

## Files

| File | Change |
|------|--------|
| `agents/evaluator.py` | **NEW** — AgentEvaluator + EvaluationResult (90 lines) |
| `agents/orchestrator.py` | **MODIFIED** — evaluate after AI analysis |
| `main.py` | **MODIFIED** — +GET /agent/evaluation |
| `docs/T35_AGENT_EVALUATION.md` | Design document |

## Verification

```
evaluate():     score=80.0
get_agent_stats: runs=1, avg=80.0
get_all_stats:   agent tracked
to_dict():       6 keys
Routes:          39
GET /agent/evaluation: 200
```
