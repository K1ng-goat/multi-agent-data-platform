# T50.5K Login Chunk Root Cause

> **Date**: 2026-06-13

---

## Chunk Mapping

```
Browser chunk:     0rdzq9nzhbghu.js
Source file:       frontend/src/app/login/page.tsx
Call site:         line 27 — fetch(`${API_BASE}/login`, ...)
API_BASE source:   frontend/src/lib/config.ts
```

## Analysis

Source code is correct:

```typescript
// config.ts
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

// login/page.tsx:27
const res = await fetch(`${API_BASE}/login`, { ... });
// This should produce: /api/login
```

## Root Cause (Same as T50.5J)

`frontend/Dockerfile` line 14 hardcoded `ARG NEXT_PUBLIC_API_URL=http://localhost:8001`.

Next.js inlines `NEXT_PUBLIC_*` env vars at build time into compiled JS bundles.
The Docker image was built with `localhost:8001` baked into every chunk:
- `0rdzq9nzhbghu.js` (login chunk)
- All other chunks using `API_BASE`

## Fix Already Applied

```
T50.5H: config.ts default → /api
T50.5I: docker-compose.yml NEXT_PUBLIC_API_URL → /api
T50.5J: Dockerfile ARG default → /api
T50.5K: THIS REPORT — verification
```

## Rebuild Required

```bash
docker compose build frontend --no-cache
docker compose up -d frontend
```

After rebuild, all chunks will use `/api` prefix.

## Files

| File | Change |
|------|--------|
| `docs/T50_5K_LOGIN_CHUNK_ROOT_CAUSE.md` | Report |
