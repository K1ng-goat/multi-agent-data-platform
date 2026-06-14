# T46 Docker Production

> **Date**: 2026-06-04  
> **Endpoint**: `GET /system/docker`

---

## Container Architecture

```
docker compose up -d
  ↓
┌──────────────────────────────────────────────────────────┐
│  backend (python:3.12-slim)    frontend (node:22-alpine) │
│  port 8000, non-root user      port 3000                 │
│  health: /database/health       health: /                │
│  UTF-8 locale, WAL mode                                 │
│                                                          │
│  mysql (8.0, optional)          redis (7, optional)      │
│  port 3306                      port 6379                │
│  health: mysqladmin ping         health: PING            │
└──────────────────────────────────────────────────────────┘
  Volumes: session_data, exports, mysql_data
```

## Backend Dockerfile Improvements

```
+ non-root user (appuser)
+ UTF-8 locale (C.UTF-8)
+ WAL + FK pragma
+ healthcheck endpoint
```

## Frontend Dockerfile

```
Multi-stage build: builder → runner
npm mirror for network resilience
Next.js production server
```

## Files

| File | Change |
|------|--------|
| `backend/Dockerfile` | **MODIFIED** — +non-root user |
| `.env.docker` | **NEW** — Docker env template |
| `main.py` | **MODIFIED** — +GET /system/docker |
| `docs/T46_DOCKER_PRODUCTION.md` | Design document |

## Verification

```
/system/docker:    200, services=[backend,frontend,redis,mysql]
/database/health:  200
/database/info:    11 tables
Routes:            60
```