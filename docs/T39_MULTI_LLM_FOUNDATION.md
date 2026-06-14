# T39 Multi-LLM Foundation

> **Date**: 2026-06-04  
> **Endpoints**: `GET /models`, `GET /model/router`

---

## Architecture

```
Agent / Orchestrator
  ↓
ModelRouter.route(task_type)
  ↓
ProviderRegistry.get("deepseek")
  ↓
DeepSeekProvider.generate(prompt)
  ↓
DeepSeek API
```

## Providers (5)

```
deepseek   enabled: true        (active)
openai     enabled: false       (stub — API key missing)
claude     enabled: false       (stub)
gemini     enabled: false       (stub)
qwen       enabled: false       (stub)
```

## Routing Table

```
chat       → deepseek
analysis   → deepseek
planner    → deepseek
report     → deepseek
audit      → deepseek
```

## API

```
GET /models        → 5 providers with enabled status
GET /model/router  → routing table (all → deepseek)
```

## Zero Behavior Change

All existing DeepSeek API calls remain in their original locations.
The provider abstraction layer is additive — it wraps but does not replace.

## Files

| File | Change |
|------|--------|
| `llm/__init__.py` | **NEW** |
| `llm/base_provider.py` | **NEW** — abstract interface |
| `llm/deepseek_provider.py` | **NEW** — wraps existing calls |
| `llm/provider_registry.py` | **NEW** — 5 providers |
| `llm/model_router.py` | **NEW** — all routes → deepseek |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T39_MULTI_LLM_FOUNDATION.md` | Design document |

## Verification

```
Models:        5 (1 enabled, 4 stubs)
Router:        5 tasks → deepseek
Routes:        48
/analyze:      200 (unchanged)
/chat:         200 (unchanged)
```