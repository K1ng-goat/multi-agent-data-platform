# T47 Nginx Reverse Proxy

> **Date**: 2026-06-04  
> **Endpoint**: `GET /system/nginx`

---

## Architecture

```
Browser → Nginx (:80)
            ├── /          → frontend:3000   (Next.js)
            ├── /api/*     → backend:8000    (FastAPI)
            └── /_next/*   → frontend:3000   (static assets)
```

## Nginx Config

```nginx
upstream frontend { server frontend:3000; }
upstream backend  { server backend:8000;  }

location /       → proxy_pass http://frontend;
location /api/   → rewrite ^/api/(.*) /$1; proxy_pass http://backend;
location /_next/ → proxy_pass http://frontend;
```

## Access Pattern

```
Before:  http://localhost:3000/           (frontend directly)
         http://localhost:8001/themes      (backend directly)

After:   http://localhost/                 (nginx → frontend)
         http://localhost/api/themes       (nginx → backend)
```

## Files

| File | Change |
|------|--------|
| `nginx/nginx.conf` | **NEW** — Reverse proxy config |
| `docker-compose.yml` | **MODIFIED** — +nginx service |
| `main.py` | **MODIFIED** — +GET /system/nginx |
| `docs/T47_NGINX_REVERSE_PROXY.md` | Design document |

## Verification

```
/system/nginx:  {enabled: true}
Routes:         61
```