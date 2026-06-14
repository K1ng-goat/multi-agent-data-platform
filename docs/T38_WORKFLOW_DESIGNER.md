# T38 Workflow Designer

> **Date**: 2026-06-04  
> **Endpoints**: `GET /workflows`, `GET /workflow/templates`, `POST /workflow/run`

---

## Workflow Templates (5)

```
financial_analysis   Data+Audit+Chart+Report       (finance)
quality_audit        Data+Audit                    (quality)
chart_dashboard      Data+Chart                    (visualization)
full_report          6 agents (all)                (report)
quick_summary        DataAgent only                (general)
```

## Structure

```python
WorkflowDefinition:
    name, description, agents[], tools[], category
```

## API

```
GET  /workflows           → ["chart_dashboard","financial_analysis",...]
GET  /workflow/templates  → full definitions
POST /workflow/run        → {"name":"quality_audit"} → matching workflow
```

## Files

| File | Change |
|------|--------|
| `workflow_definition.py` | **NEW** — WorkflowDefinition + 5 templates (95 lines) |
| `main.py` | **MODIFIED** — +3 endpoints |
| `docs/T38_WORKFLOW_DESIGNER.md` | Design document |

## Verification

```
Templates:            5 names
full_report:          6 agents
run():                ok
list_all():           5 definitions
Routes:               46
GET /workflows:       5
GET /templates:       5
POST /run:            ok
```
