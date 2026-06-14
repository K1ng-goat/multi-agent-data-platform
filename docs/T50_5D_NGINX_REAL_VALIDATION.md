# T50.5D Nginx Real Validation

> **Date**: 2026-06-13

---

## Results

### Reverse Proxy Verified

```
Browser → :80 (Nginx) → routes:

  /api/             → backend:8000  → 200
  /api/themes       → backend:8000  → 200
  /api/database/info→ backend:8000  → 200
  /                 → frontend:3000 → 200
```

### Nginx Access Logs

```
172.18.0.1 - "GET /api/ HTTP/1.1" 200
172.18.0.1 - "GET /api/themes HTTP/1.1" 200
172.18.0.1 - "GET /api/database/info HTTP/1.1" 200
```

### Port Mapping

```
:80    → nginx      (public entry)
:3000  → frontend   (direct)
:8001  → backend    (direct)
:3307  → mysql      (direct)
:6379  → redis      (internal, Docker network only)
```

### Direct Access (bypass Nginx)

```
localhost:8001  → backend   200
localhost:3000  → frontend  200
```

## Files

| File | Change |
|------|--------|
| `docs/T50_5D_NGINX_REAL_VALIDATION.md` | Report |
