# T50 Production Deployment

> **Date**: 2026-06-04  
> **Endpoints**: `GET /system/deployment`, `GET /system/health`

---

## Architecture

```
Browser → Nginx (:80) → Frontend (:3000)
                      → Backend (:8000) → Redis (:6379)
                                        → SQLite / MySQL
                      ← Monitoring (T48)
                      ← CI/CD (T49)
```

## Deployment Profile

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Additional services in production:
- `nginx` (reverse proxy, port 80)
- `redis` (cache, health: PING)
- All services: `restart: always`

## Scripts

```
scripts/start.sh      — docker compose up + health check
scripts/stop.sh       — docker compose down
scripts/restart.sh    — docker compose restart
scripts/backup.sh     — backup SQLite + session data + exports
```

## System Endpoints

```
/system/deployment  → {production_ready, docker, nginx, monitoring, cicd}
/system/health      → {database, cache, agents} health check
```

## Files

| File | Change |
|------|--------|
| `docker-compose.prod.yml` | **NEW** — Production override |
| `.env.production` | **NEW** — Production environment |
| `scripts/{4 files}` | **NEW** — Deploy scripts |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T50_PRODUCTION_DEPLOYMENT.md` | Design document |

## Verification

```
/system/deployment:  {production_ready: true, nginx: true, monitoring: true, cicd: true}
/system/health:      {database: ok, cache: ok, agents: ok}
Routes:              68
```