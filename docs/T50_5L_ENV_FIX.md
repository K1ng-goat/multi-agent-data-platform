# T50.5L Environment Variable Fix

> **Date**: 2026-06-14

---

## Root Cause

`docker-compose.yml` used `${DEEPSEEK_API_KEY:-sk-placeholder}` in `environment:`.
The `${VAR:-default}` syntax reads from the HOST shell, NOT from `env_file`.
Since the host shell had no `DEEPSEEK_API_KEY`, it always defaulted to `sk-placeholder`.

## Fix

1. Added `env_file: .env.production` to backend service in both compose files
2. Removed `DEEPSEEK_API_KEY` from `environment:` block (handled by `env_file` now)

## Files Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | +`env_file`, removed `DEEPSEEK_API_KEY` override |
| `docker-compose.prod.yml` | already had `env_file`, removed `DEEPSEEK_API_KEY` override |

## Verification

```
docker exec data-agent-backend sh -c 'echo $DEEPSEEK_API_KEY'
→ DEEPSEEK_API_KEY=sk-82a6e89fd0... (real key, not sk-placeholder)

/themes:        200
/database/info: 200
```
