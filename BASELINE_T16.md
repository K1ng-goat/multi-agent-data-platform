# BASELINE — T16 Freeze

> **Date**: 2026-06-04
> **Branch**: main (ahead of origin/main by 3 commits)
> **Project Version**: T16

---

## Project Health

```
Backend:    30 routes, AI Excel Data Agent
Database:   SQLite (10 tables, verified)
Docker:     Backend container healthy (port 8001)
Frontend:   Local build passes, Docker build blocked (network)
Memory:     Stable, all D1-D8 fixes applied
Session:    L1 (dict) + L2 (SessionStore) cache-through architecture
```

## Commit History

```
2eb4fb0 refactor: unify intent classification
57b75a1 feat: enable sqlite wal and foreign keys
3649768 feat: reliability sprint batch1
69837e7 fix: improve memory system consistency
42aa72e Initial commit
```

## Sprint Completion Status

| Sprint | Description | Status |
|--------|-------------|--------|
| B1 | Auth (T3), Validation (T4), Rate Limit (T9), Size Limit (T10) | DONE |
| B2 | WAL + FK Pragma (T5), Intent Unification (T6) | DONE |
| Memory Fix | D1-D8: preference category filter, truncation, conversation bidirectional, except logging | DONE |
| T1 Ph1-3 | SessionStore infrastructure, dual-write, fallback read, restart resilience | DONE |
| T7 Ph0 | Preference dual-write (user_preferences + user_memories sync) | DONE |
| T15 | Backend Docker UTF-8 fix + build | DONE |
| T16 Ph1-3 | MySQL infrastructure, ORM compatibility (56 fixes), SQLite regression | DONE |
| T16 Ph4 | MySQL runtime validation | BLOCKED (Docker Hub) |

## Technical Debt Register

| ID | Item | Priority | Blocked By |
|----|------|----------|------------|
| TD-01 | MySQL runtime validation (T16 Ph4) | HIGH | Docker Hub network |
| TD-02 | Frontend Docker build + validation | HIGH | Docker Hub network |
| TD-03 | Preference table merge (T7 Ph1) | MEDIUM | Deferred |
| TD-04 | FK constraints (T2) | MEDIUM | SQLite 9-table rebuild risk |
| TD-05 | API versioning (T8) | LOW | Requires frontend URL changes |
| TD-06 | Remove sessions dict (T1 Ph4) | LOW | Rejected — L1 cache stable |
| TD-07 | Dashboard + reports merge (T11) | LOW | Deferred |
| TD-08 | Structured logging (T12) | LOW | Deferred |
| TD-09 | Automated tests (T13) | MEDIUM | Deferred |
| TD-10 | Docker cleanup_expired() never called | LOW | Deferred |
| TD-11 | Git push blocked | HIGH | GitHub auth/network |

## Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R-01 | Docker Hub unreachable — blocks mysql:8.0 + node:22-alpine pulls | HIGH | Use cached python:3.12-slim; backend already built. Monitor network. |
| R-02 | SQLite → MySQL migration never tested at runtime | MEDIUM | DB_ENGINE=sqlite default ensures zero impact. Phase 4 validates when unblocked. |
| R-03 | Frontend container never built in Docker | MEDIUM | npm run build passes locally. Dockerfile syntax correct. |
| R-04 | All uncommitted changes in working tree (26 modified + 9 untracked) | MEDIUM | git stash pop available; no data loss risk. Commit when stable. |
| R-05 | Session history not persisted to SessionStore | LOW | chat_messages + conversation_memories tables persist history independently |

## Unblock Commands

When Docker Hub is reachable:

```bash
# T16 Phase 4
docker pull mysql:8.0
docker compose up -d mysql backend
docker compose ps

# T15 Frontend
docker pull node:22-alpine
docker compose build frontend
docker compose up -d frontend
```

## Modified Files (Working Tree)

```
26 modified files (backend: 16, frontend: 9, root: 1)
 9 untracked files (Dockerfiles, session infra, docker-compose)
 5 commits on main
```
