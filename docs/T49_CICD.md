# T49 CI/CD Pipeline

> **Date**: 2026-06-04  
> **Endpoint**: `GET /system/cicd`

---

## Workflow Files

```
.github/workflows/
├── backend.yml     (push/pull_request, paths: backend/**)
└── frontend.yml    (push/pull_request, paths: frontend/**)
```

## Backend Pipeline

```yaml
runs-on: ubuntu-latest
steps:
  1. checkout
  2. setup-python 3.11
  3. pip install -r requirements.txt
  4. python -c "from main import app"    (verify imports)
  5. uvicorn main:app &                  (start server)
  6. curl /database/health               (health check)
  7. curl /themes                        (route check)
```

## Frontend Pipeline

```yaml
runs-on: ubuntu-latest
steps:
  1. checkout
  2. setup-node 22
  3. npm ci
  4. npm run build
  5. test -d .next                       (verify output)
```

## Files

| File | Change |
|------|--------|
| `.github/workflows/backend.yml` | **NEW** — Backend CI |
| `.github/workflows/frontend.yml` | **NEW** — Frontend CI |
| `main.py` | **MODIFIED** — +GET /system/cicd |
| `docs/T49_CICD.md` | Design document |

## Verification

```
/system/cicd:  {enabled: true}
Routes:        66
```