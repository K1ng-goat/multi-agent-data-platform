# Technical Debt Register

> **Date**: 2026-06-04  
> **Baseline**: T20 Production Readiness Review

---

## Summary

```
Total items:     11
Must Fix:         0
Should Fix:       2
Can Fix Later:    6
Nice to Have:     3
```

---

## Should Fix Before Release

| ID | Item | Priority | Effort | Owner |
|----|------|----------|--------|-------|
| TD-01 | Git commit + push (26 modified, 9 new files) | SHOULD | 5 min | Dev |
| TD-02 | Set JWT_SECRET env var in production | SHOULD | 1 min | Ops |

## Can Fix After Release

| ID | Item | Priority | Effort | Blocked By |
|----|------|----------|--------|------------|
| TD-03 | T19 MySQL runtime validation | CAN | 30 min | Docker Hub network |
| TD-04 | cleanup_expired() scheduling | CAN | 20 min | — |
| TD-05 | Structured logging (logging module) | CAN | 2h | — |
| TD-06 | API versioning (/api/v1/ prefix) | CAN | 2h | Frontend URL updates |
| TD-07 | Dashboard + reports table merge | CAN | 3h | Data migration |
| TD-08 | Preference table merge (T7 Ph1) | CAN | 2h | Data migration |

## Nice to Have

| ID | Item | Priority | Effort |
|----|------|----------|--------|
| TD-09 | pytest automated test suite | NICE | 4h |
| TD-10 | Docker health dashboards | NICE | 4h |
| TD-11 | Alembic migration framework | NICE | 3h |

## Resolved / Rejected

| ID | Item | Resolution |
|----|------|------------|
| T1 Ph4 | Delete sessions dict | REJECTED — L1+L2 cache-through stable |
| T2 | FK constraints (9-table rebuild) | REJECTED — SQLite risk > benefit |
| T5 | WAL + FK pragma | RESOLVED — database.py event listener |
| T6 | Intent classifier duplication | RESOLVED — intent_classifier.py unified |
| T16 | MySQL integration (code) | RESOLVED — ORM 56 fixes, DB_ENGINE branching |

## Debt by Category

```
Security:     1 (JWT_SECRET hardcoded fallback)
Reliability:  2 (cleanup_expired, structured logging)
Code Quality: 3 (API versioning, table merge, test suite)
Operations:   2 (MySQL validation, Docker health dashboards)
Process:      1 (git commit pending)
Infrastructure: 1 (Alembic migrations)
```
