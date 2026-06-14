# T23 Agent Orchestrator Refactor

> **Date**: 2026-06-04  
> **Baseline**: v1.0  
> **Goal**: Extract /analyze business logic into AgentOrchestrator pipeline

---

## Old Flow (Before T23)

```
POST /analyze (main.py, ~200 lines inline)

  _validate_excel_upload(file)
  pd.read_excel()
  _convert_excel_dates(df)
  _generate_charts(df)
  _build_data_summary(df)
  sessions[sid] = {...}
  _load_preferences(sid)
  DeepSeek API call (inline prompt)
  ds.update_snapshot()
  mgr.save_workspace()
  mgr.save_analysis_memory()
  session_store.save()
  return {session_id, data_summary, charts, analysis}
```

## New Flow (After T23)

```
POST /analyze (main.py, 16 lines)

  _validate_excel_upload(file)
  contents = await file.read()
  result = await orchestrator.run_analysis_pipeline(...)
  return result

                ↓

AgentOrchestrator.run_analysis_pipeline() (orchestrator.py, 63 lines)
  │
  ├── pd.read_excel()
  ├── _convert_excel_dates()     (private helper)
  ├── _generate_charts()         (private helper)
  ├── _build_data_summary()      (private helper)
  ├── sessions[sid] = {...}
  ├── _load_preferences()        (private helper)
  ├── _ai_analyze() or fallback  (private helper)
  ├── _persist_dashboard()       (private helper)
  ├── _persist_memory()          (private helper)
  └── session_store.save()
```

## Affected Files

| File | Change | Lines |
|------|--------|-------|
| `agents/orchestrator.py` | **NEW** — AgentOrchestrator class + 7 helpers | +293 |
| `main.py` | **MODIFIED** — /analyze reduced from ~200 to 16 | -184 |

## Compatibility Analysis

| Concern | Status |
|---------|--------|
| API response format | IDENTICAL — same keys, same types |
| Session creation | IDENTICAL — same sessions dict + SessionStore |
| DeepSeek prompt | IDENTICAL — same prompt template, same temperature |
| Memory persistence | IDENTICAL — same mgr.save_*() calls |
| Dashboard/report | IDENTICAL — same ds.update_snapshot() |
| Error handling | IDENTICAL — same try/except patterns |
| Frontend changes | NONE — response identical |
| Route signature | IDENTICAL — same path, params, decorators |

## Verification

```
1.  30 routes loaded
2.  /register OK
3.  /analyze: 200 — session_id returned
4.  data_summary keys: [filename, shape, columns, dtypes, describe, sample, null_counts]
5.  charts: 3 (line, bar, pie)
6.  analysis: [summary, anomaly, trend]
7.  SessionStore persisted: True
8.  /chat: 200 mode=chat
9.  /reports: 200
10. /dashboard: 200 has_data=True
11. /export/excel: 200
12. AgentOrchestrator instance: OK
```

## Architecture Improvement

```
BEFORE                          AFTER
┌──────────┐                   ┌──────────┐
│ main.py  │ 4200 lines        │ main.py  │ 4016 lines (-184)
│ /analyze │ ~200 lines        │ /analyze │ 16 lines
│ inline   │                   │ thin     │
└──────────┘                   └────┬─────┘
                                    │ calls
                              ┌─────▼──────────┐
                              │ orchestrator.py│ 293 lines
                              │ AgentOrchestr. │
                              │ pipeline()     │
                              └────────────────┘

Route layer: validate → orchestrate → return
Business logic: encapsulated in orchestrator
```
