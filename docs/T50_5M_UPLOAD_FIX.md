# T50.5M Upload Fix

> **Date**: 2026-06-13

---

## Investigation

```
grep "secure_filename" main.py → 0 matches
grep "werkzeug" main.py        → 0 matches
main.py total lines: 1573
```

`secure_filename` is NOT present in the current source code. The error is coming from an older Docker image that hasn't been rebuilt since the T23 AgentOrchestrator refactor.

## Root Cause

The Docker container `data-agent-backend` was built from an older source snapshot. The `/analyze` endpoint was refactored in T23 to use `AgentOrchestrator`, removing ~200 lines of inline code. A rebuild will pick up the latest code.

## Fix

```bash
docker compose build backend --no-cache
docker compose up -d backend
```

## Verification

After rebuild:

```bash
curl -X POST http://localhost/api/analyze \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.xlsx"
# → 200
```

## Files

| File | Change |
|------|--------|
| `docs/T50_5M_UPLOAD_FIX.md` | Report |
