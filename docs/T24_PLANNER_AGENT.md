# T24 Planner Agent

> **Date**: 2026-06-04  
> **Baseline**: T23 AgentOrchestrator  
> **Goal**: Add planning layer above orchestration

---

## Architecture

```
BEFORE (T23)                          AFTER (T24)
─────────────                         ────────────
/analyze                              /analyze
  ↓                                     ↓
AgentOrchestrator                      AgentOrchestrator
  ↓                                     ↓
Always runs:                         PlannerAgent.plan()
  Data → Audit → Chart → Report        ↓
                                   Conditional execution:
                                     Audit? KPI? Charts? Report?
```

## Plan Schema

```python
@dataclass
class AnalysisPlan:
    run_audit: bool = True       # data quality check
    run_kpi: bool = True         # AI statistical analysis
    run_charts: bool = True      # chart generation
    run_report: bool = True      # report generation
    run_style: bool = False      # style application

    chart_types: list[str]       # ["line","bar","pie"] — hints
    kpi_targets: list[str]       # ["Sales","Revenue"] — best columns
```

## Planner Heuristics

| Condition | Decision |
|-----------|----------|
| No numeric columns | `run_kpi=False`, `run_charts=False` |
| < 2 rows | `run_charts=False` |
| Has null counts | `run_audit=True` (forced) |
| Intent = "audit" | Only audit |
| Intent = "chart" | Only charts |
| Intent = "full_report" | All steps enabled |
| Small dataset (≤10 rows) | chart_types = ["bar","pie"] |
| Large dataset (>10 rows) | chart_types = ["line","bar","pie"] |

## Execution Examples

### Example 1 — Small sales dataset
```
data: {rows:10, Sale:int64, Region:object}
intent: analyze
→ audit=True, kpi=True, charts=True (bar+pie), report=True
```

### Example 2 — Audit-only request
```
data: {rows:100, A:int64, B:float64}
intent: audit
→ audit=True, kpi=False, charts=False, report=False
```

### Example 3 — Chart-only request
```
data: {rows:50, Date:object, Value:float64}
intent: chart
→ audit=False, kpi=False, charts=True (line+bar+pie), report=False
```

### Example 4 — Single-row dataset
```
data: {rows:1, Name:object}
intent: analyze
→ audit=False, kpi=False, charts=False, report=False
```

## Files

| File | Change |
|------|--------|
| `agents/planner_agent.py` | **NEW** — PlannerAgent + AnalysisPlan (95 lines) |
| `agents/orchestrator.py` | **MODIFIED** — accepts plan, conditional execution (+10 lines) |
| `main.py` | **MODIFIED** — imports PlannerAgent (+2 lines) |

## Backward Compatibility

- No plan provided → all steps run (identical to T23 behavior)
- Plan provided → conditional execution
- `/analyze` response format unchanged
- Frontend unchanged

## Future Extensions

The PlannerAgent is designed for these future agents:

```python
# ForecastAgent — time-series prediction
if plan.get("run_forecast") and has_date_column:
    result = await forecast_agent.execute(context)

# AnomalyAgent — statistical outlier detection
if plan.get("run_anomaly"):
    result = await anomaly_agent.execute(context)

# RecommendationAgent — business suggestions
if plan.get("run_recommendation"):
    result = await recommendation_agent.execute(context)
```

Extending requires:
1. Add boolean flag to `AnalysisPlan`
2. Add heuristic to `PlannerAgent.plan()`
3. Add execution block to `AgentOrchestrator.run_analysis_pipeline()`

## Verification

```
Routes:            30 loaded
/analyze no plan:  200 (backward compat)
Planner plan:      audit=True kpi=True charts=True report=True
Intent=audit:      audit=True kpi=False
Intent=chart:      kpi=False charts=True
Null data:         audit forced True
.to_dict():        7 keys
/chat:             200
/export:           200
API compat:        IDENTICAL
Frontend changes:  0
```
