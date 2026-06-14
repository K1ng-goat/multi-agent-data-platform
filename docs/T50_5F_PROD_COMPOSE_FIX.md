# T50.5F Production Compose Fix

> **Date**: 2026-06-13

---

## Root Cause

`docker-compose.prod.yml` was an overlay file without `build` or `image` definitions.
When used standalone (`docker compose -f docker-compose.prod.yml`), Docker couldn't resolve the frontend/backend services.

## Fix

Made `docker-compose.prod.yml` **self-contained**:

```yaml
backend:   build: ./backend    + ports + volumes + env + healthcheck
frontend:  build: ./frontend   + ports + env
nginx:     image: nginx:alpine  + ports + volume
redis:     image: redis:7-alpine + healthcheck
mysql:     image: mysql:8.0     + ports + volume + env + healthcheck
```

Now works both standalone and as overlay.

## Verification

```
docker compose -f docker-compose.prod.yml config → VALID
/themes     → 200
Frontend /  → 200
```

## Files

| File | Change |
|------|--------|
| `docker-compose.prod.yml` | **MODIFIED** — self-contained |
| `docs/T50_5F_PROD_COMPOSE_FIX.md` | Report |
