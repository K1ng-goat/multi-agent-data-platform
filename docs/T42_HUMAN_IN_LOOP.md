# T42 Human-in-the-Loop Approval

> **Date**: 2026-06-04  
> **Endpoints**: `GET /workflow/pending`, `POST /workflow/approve/{id}`, `POST /workflow/reject/{id}`

---

## Architecture

```
Workflow executes:
  DataAgent OK
  AuditAgent OK
  ↓
  approval_store.request(wf_id, "ReportAgent")
  ↓
  WAIT ──→ Human reviews ──→ approve / reject
  ↓
  (if approved) ReportAgent → ExportAgent
```

## API

```
GET  /workflow/pending              → list pending approvals
POST /workflow/approve/{wf_id}      → approve + trace recorded
POST /workflow/reject/{wf_id}       → reject + trace recorded
```

## Approval States

```
WAITING   → pending human decision
APPROVED  → workflow continues
REJECTED  → workflow stops
NONE      → no approval exists for this workflow
```

## File

| File | Change |
|------|--------|
| `approval_store.py` | **NEW** — ApprovalStore (80 lines) |
| `main.py` | **MODIFIED** — +3 endpoints |
| `docs/T42_HUMAN_IN_LOOP.md` | Design document |

## Verification

```
request():       WAITING
approve():       APPROVED
reject():        REJECTED
get_status:      OK (APPROVED/REJECTED/NONE)
GET /pending:    200
POST /approve:   ok
POST /reject:    ok (nonexistent → error)
Routes:          52
```