# T50.5I Remove Remaining localhost:8001 References

> **Date**: 2026-06-13

---

## Search Results

```
grep "8001|localhost:800" frontend/src/ → 0 matches
```

Zero hardcoded `localhost:8001` references remain in source code.

## Action Taken

- Rebuilt frontend Docker image (`--no-cache`) to bake in the new `/api` default
- Frontend now calls same-origin `/api/*` for all backend requests

## End-to-End Nginx Verification

```
/api/              200    (health)
/api/themes         200    (4 themes)
/api/database/info  200    (11 tables, MySQL)
/api/register       200    (token returned)
/api/me             200    (user=nginx_test, valid JWT)
Frontend :3000      200
Frontend via Nginx  200
```

## Files

| File | Change |
|------|--------|
| `frontend/src/lib/config.ts` | Default → `/api` (T50.5H) |
| `docker-compose.yml` | `NEXT_PUBLIC_API_URL=/api` (T50.5H) |
| `docs/T50_5I_REMOVE_HARDCODED_API.md` | Report |
