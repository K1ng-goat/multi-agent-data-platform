# Project Metrics

> **Version**: 1.0  
> **Date**: 2026-06-04  
> **E2E**: 39/39 PASSED

---

## Routes (29)

```
Auth:     3  (/register, /login, /me)
Core:     4  (/upload, /analyze, /chat, /agent-chat)
Workflow: 1  (/workflow)
Memory:   7  (/memory/preferences, /recent, /conversations, /retrieve, /summary, /clear)
Dashboard:1  (/dashboard)
Reports:  2  (/reports, /reports/{id})
Style:    3  (/themes, /style/apply, /style/preview/{id})
Export:   3  (/export/excel/{id}, /export/word/{id}, /export/chart/{id}/{n})
Docs:     3  (/docs, /redoc, /openapi.json)
Health:   2  (/, health check)
```

## Database (10 tables, 85 columns)

```
users                  5c   (id, username, email, password_hash, created_at)
chat_messages          6c   (id, session_id, user_id, role, content, created_at)
dashboard_snapshot    13c   (id, session_id, user_id, filename, rows, columns, kpi, ...)
reports               12c   (id, session_id, user_id, filename, summary, anomaly, trend, ...)
user_preferences       4c   (id, user_id, key, value)
user_memories          6c   (id, user_id, category, key, value, updated_at)
workspace_memories    10c   (id, user_id, session_id, filename, data_summary, ...)
conversation_memories  8c   (id, user_id, session_id, role, content, mode, steps_json, created_at)
analysis_memories      9c   (id, user_id, session_id, filename, kpi_json, ...)
sessions              12c   (id, session_id, user_id, filename, data_summary_json, ...)
```

## Docker Services

```
data-agent-backend     python:3.12-slim    875MB    8001:8000
data-agent-frontend    node:22-alpine       —       3000:3000
data-agent-mysql       mysql:8.0           —       3307:3306  (pending)
```

## Agents (7)

```
DataMasterAgent    — orchestration, intent classification, routing
DataAgent          — statistical analysis, DeepSeek AI analysis
ChartAgent         — line/bar/pie chart generation
AuditAgent         — data quality audit, null/duplicate/outlier detection
ReportAgent        — markdown report generation via DeepSeek
StyleAgent         — theme detection, Chinese font/size/color parsing
ExportAgent        — Excel (.xlsx), Word (.docx), Chart (.png) export
```

## Memory (4 layers)

```
L1  User Memory          — key-value preferences, category-tagged
L2  Workspace Memory     — session snapshots (data, charts, analysis)
L3  Conversation Memory  — chat history (user + AI, bidirectional)
L4  Analysis Memory      — KPI extraction, trend/anomaly storage
```

## Test Coverage

```
E2E Integration:   39 tests, 39 passed (100%)
Unit:              0 (not implemented)
Static Analysis:   flake8 (11 pre-existing), mypy (10 pre-existing)
Security:          bandit (0 HIGH, 1 MEDIUM)
```

## Code Metrics

```
Backend files:     ~35
Frontend files:    ~15
Python LOC:        ~4,200
TypeScript LOC:    ~2,500
Total commits:     5
Modified files:    26 (uncommitted)
New files:         9 (uncommitted)
```

## Release Score

```
Backend Stability:    100  (39/39 E2E, 0 crashes)
Frontend Runtime:      90  (Docker serving)
Database:              85  (SQLite prod-ready, MySQL code-ready)
Security:              85  (JWT+bcrypt+rate-limit+validation)
Deployment:            80  (Docker backend+frontend, MySQL blocked)
Code Quality:          80  (0 new issues from T16)

OVERALL:               87 / 100
```

## Sprints Completed

```
B1   Auth, Validation, Rate Limit, Size Limit    (T3/T4/T9/T10)
B2   WAL + FK Pragma, Intent Unification         (T5/T6)
MEM  Memory System Fixes (D1-D8)
T1   Session Persistence (Phases 1-3)
T7   Preference Dual-Write (Phase 0)
T15  Backend Docker UTF-8 + Build
T16  MySQL Integration (Phases 1-3)
T17  E2E Validation (39/39)
T18  Frontend Docker Build
T20  Production Readiness Review
T21  Release Packaging
```
