# T45 MySQL Migration

> **Date**: 2026-06-04  
> **Endpoints**: `GET /database/info`, `GET /database/health`

---

## Architecture

```
DATABASE_TYPE=sqlite  (default)     DATABASE_TYPE=mysql
─────────────────────               ─────────────────────
sqlite:///data_agent.db              mysql+pymysql://user:pass@host:3306/db
WAL mode enabled                     pool_size=5, pre_ping=True
FK pragma ON                         InnoDB (FK by default)

     pymysql not installed?           MySQL unreachable?
     → auto-fallback to SQLite        → auto-fallback to SQLite
```

## Environment

```bash
DATABASE_TYPE=sqlite     # default
DATABASE_TYPE=mysql      # MySQL mode

# MySQL only:
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=agent_db
```

## API

```
GET /database/info   → {"database_type":"sqlite","engine":"SQLite","tables":11}
GET /database/health → {"ok":true,"database_type":"sqlite"}
```

## Fallback Strategy

```
DATABASE_TYPE=mysql
  ↓
try: import pymysql → create engine → connect
  ↓ fail? (ImportError, OperationalError)
  ↓
DATABASE_TYPE := sqlite
engine := sqlite:///data_agent.db
→ continues normally
```

## Files

| File | Change |
|------|--------|
| `database.py` | **MODIFIED** — DATABASE_TYPE, get_database_url(), get_database_info(), auto-fallback |
| `main.py` | **MODIFIED** — +GET /database/info, +GET /database/health |
| `docs/T45_MYSQL_MIGRATION.md` | Design document |

## Verification

```
SQLite mode:     DB_ENGINE=sqlite, 11 tables
MySQL fallback:  engine created, connection refused → would fall back at startup
/database/info:  200
/database/health: 200
/analyze:        200
Routes:          59
ORM models:      all VARCHAR(255) + TEXT (T16 Phase 2)
```