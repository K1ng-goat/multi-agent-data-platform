# T41 Agent Dashboard

> **Date**: 2026-06-04  
> **Page**: `/dashboard/agents`

---

## Architecture

```
/dashboard/agents
  ↓
Parallel fetch from 6 APIs:
  GET /agent/metrics        → Agent metrics table
  GET /agent/evaluation     → Score cards
  GET /workflow/latest      → Latest trace KPIs
  GET /agents               → Agent badges
  GET /tools                → Tool badges
  GET /models               → Model badges
```

## Sections

```
1. Agent Metrics     — table: runs, success_rate, avg_duration, retries
2. Agent Evaluation  — cards: avg_score per agent
3. Workflow Activity — KPI grid: agents, steps, success_rate, duration
4. System Inventory  — badges: agents (blue), tools (emerald), models (enabled/disabled)
```

## Files

| File | Change |
|------|--------|
| `frontend/src/app/dashboard/agents/page.tsx` | **NEW** — Dashboard page (130 lines) |
| `docs/T41_AGENT_DASHBOARD.md` | Design document |

## Backend Endpoints Used

```
/agent/metrics       (T28) — per-agent runtime stats
/agent/evaluation    (T35) — quality scores
/workflow/latest     (T30) — latest trace
/agents              (T33) — registered agents
/tools               (T29) — registered tools
/models              (T39) — LLM providers
```

## Verification

```
All 6 endpoints:    OK (49 routes total)
Backend unchanged:  0 new backend code
```