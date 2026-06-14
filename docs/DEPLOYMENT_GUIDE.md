# Deployment Guide

> **Version**: 1.0  
> **Last Updated**: 2026-06-04

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Python | 3.11+ |
| Node.js | 20+ (local frontend only) |
| Docker | 29.5+ (for container deployment) |
| DeepSeek API Key | Required for AI features |

---

## Option 1 — Local Deployment (Quick Start)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
set DEEPSEEK_API_KEY=sk-your-key    # Windows
# export DEEPSEEK_API_KEY=sk-...    # macOS/Linux

python main.py
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Verify

```bash
curl http://localhost:8000/
# → {"message":"AI Excel Data Agent API is running"}

curl http://localhost:8000/themes
# → [4 themes with Chinese names]
```

---

## Option 2 — Docker Deployment

### Prerequisites

```bash
docker pull python:3.12-slim
docker pull node:22-alpine
```

### Build & Start

```bash
docker compose build
docker compose up -d
docker compose ps
```

```
NAME                  STATUS                 PORTS
data-agent-backend    Up (healthy)           8001→8000
data-agent-frontend   Up                     3000→3000
```

### Access

```
Frontend:  http://localhost:3000
Backend:   http://localhost:8001
```

### Stop

```bash
docker compose down
```

---

## Option 3 — Docker + MySQL

### Prerequisites

```bash
docker pull mysql:8.0
```

### Configure

Edit `docker-compose.yml` backend environment:

```yaml
environment:
  - DB_ENGINE=mysql
  - MYSQL_HOST=mysql
  - MYSQL_USER=data_agent
  - MYSQL_PASSWORD=changeme
  - MYSQL_DATABASE=data_agent
```

### Start

```bash
docker compose up -d mysql
docker compose up -d backend frontend
docker compose ps
```

```
NAME                  STATUS
data-agent-mysql      Up (healthy)
data-agent-backend    Up (healthy)
data-agent-frontend   Up
```

### Verify MySQL Connection

```bash
docker logs data-agent-backend | grep mysql
# → mysql+pymysql://data_agent:***@mysql:3306/data_agent
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | Yes | — | DeepSeek API key |
| `DB_ENGINE` | No | `sqlite` | `sqlite` or `mysql` |
| `MYSQL_HOST` | MySQL only | `localhost` | MySQL host |
| `MYSQL_PORT` | MySQL only | `3306` | MySQL port |
| `MYSQL_USER` | MySQL only | `data_agent` | MySQL user |
| `MYSQL_PASSWORD` | MySQL only | `changeme` | MySQL password |
| `MYSQL_DATABASE` | MySQL only | `data_agent` | MySQL database |
| `JWT_SECRET` | No | Built-in fallback | JWT signing secret |
| `RATE_LIMIT_REQUESTS` | No | `10` | Rate limit count |
| `RATE_LIMIT_WINDOW_SEC` | No | `60` | Rate limit window |

---

## Database

### SQLite (Default)

```
data_agent.db  — auto-created on first startup
WAL mode:      enabled (better concurrency)
FK enforcement: enabled
```

### MySQL

```
Requires MySQL 8.0 running
Set DB_ENGINE=mysql
Tables auto-created by init_db()
10 tables, MySQL 8.0 compatible (all VARCHAR have length, TEXT has no defaults)
```

### Switching

```
SQLite → MySQL:  Set DB_ENGINE=mysql, restart
MySQL → SQLite:  Set DB_ENGINE=sqlite, restart
Note: data is NOT migrated automatically between engines.
```

---

## Troubleshooting

### "DEEPSEEK_API_KEY not set"

Analysis/chart/agent features return error messages. Upload + basic stats still work.

```bash
set DEEPSEEK_API_KEY=sk-your-key
```

### "Session expired"

Session was created before server restart and not yet persisted. Re-upload the Excel file.

### "Container not healthy"

```bash
docker compose logs backend --tail 20
# Common: missing DEEPSEEK_API_KEY, DB file permissions
```

### "Cannot pull mysql:8.0"

Docker Hub unreachable. Use SQLite mode (default) — fully functional without MySQL.

### "npm registry unreachable"

Dockerfile uses `registry.npmmirror.com` mirror. If blocked, edit Dockerfile line 8 to use a different mirror.

### WAL files (.db-shm, .db-wal)

Normal SQLite WAL artifacts. Auto-checkpointed by SQLite. Do not delete.

### session_data/ parquet files grow

`cleanup_expired()` method exists in SessionStore but is not yet scheduled. Manual cleanup:

```bash
python -c "from session_store import SessionStore; SessionStore().cleanup_expired(hours=24)"
```
