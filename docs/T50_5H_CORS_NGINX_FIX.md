# T50.5H CORS + Nginx API Routing Fix

> **Date**: 2026-06-13

---

## Root Cause

Frontend called `http://localhost:8001/...` directly (cross-origin from `http://localhost`), bypassing Nginx reverse proxy. CORS blocked these requests.

## Fix

Changed frontend API base from absolute URL to same-origin `/api`:

```
BEFORE:  API_BASE = "http://127.0.0.1:8001"  → cross-origin CORS errors
AFTER:   API_BASE = "/api"                    → same-origin via Nginx
```

## Request Flow

```
Browser: http://localhost
  ↓
Frontend calls /api/themes
  ↓
Nginx receives /api/themes
  → rewrite: /api/themes → /themes
  → proxy_pass: http://backend:8000
  ↓
Backend returns 200
  ↓
Browser: no CORS issue (same-origin)
```

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/lib/config.ts` | Default: `http://127.0.0.1:8001` → `/api` |
| `docker-compose.yml` | `NEXT_PUBLIC_API_URL` changed to `/api` |
| `docs/T50_5H_CORS_NGINX_FIX.md` | Report |

## Verification

```
Nginx /api/themes  → 200
Nginx /api/        → 200
Direct :8001       → 200  (dev mode still works)
```