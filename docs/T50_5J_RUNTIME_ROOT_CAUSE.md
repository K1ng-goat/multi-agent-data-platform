# T50.5J Runtime Root Cause

> **Date**: 2026-06-13

---

## Root Cause

`frontend/Dockerfile` line 14 had the hardcoded default:

```dockerfile
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
```

This ARG default was baked into the Next.js compiled JS bundles at build time.
Even though `config.ts` was changed to `/api`, the Dockerfile's `ENV NEXT_PUBLIC_API_URL`
overrides it during `npm run build`.

## Why grep src/ Missed It

`grep` searched `frontend/src/` which contains TypeScript source. The `config.ts` was
correctly changed to `/api`. But Next.js inlines `NEXT_PUBLIC_*` env vars at build time
into the compiled `.next/static/chunks/*.js` bundles — which are NOT in `src/`.

## Container Search Results

```
Found 8001 in:
  /app/.next/static/chunks/0dq3npqoxtudc.js    ← client bundle
  /app/.next/server/chunks/ssr/*.js              ← SSR bundle
```

## Fix

```dockerfile
# BEFORE
ARG NEXT_PUBLIC_API_URL=http://localhost:8001

# AFTER
ARG NEXT_PUBLIC_API_URL=/api
```

## Files

| File | Change |
|------|--------|
| `frontend/Dockerfile:14` | `localhost:8001` → `/api` |
| `docs/T50_5J_RUNTIME_ROOT_CAUSE.md` | Report |

## Rebuild Command

```bash
docker compose build frontend --no-cache
docker compose up -d frontend
```

Then verify:

```bash
docker exec data-agent-frontend grep -rl "8001" /app/.next/
# Should return empty — no 8001 references in compiled bundles
```
