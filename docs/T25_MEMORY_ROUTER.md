# T25 Memory Router

> **Date**: 2026-06-04  
> **Baseline**: T24 PlannerAgent  
> **Feature Flag**: `ENABLE_MEMORY_ROUTER=true` (default: off)

---

## Architecture

```
BEFORE (T24)                          AFTER (T25)
─────────────                         ────────────
/analyze                              /analyze
  ↓                                     ↓
AgentOrchestrator                      MemoryRouter.route()
  ↓                                     ↓
Always runs all agents                AgentOrchestrator
                                         ↓
                                      memory_context injected into AI prompt
```

## Routing Rules

| Plan Flag | Memory Layers Retrieved | Reason |
|-----------|----------------------|--------|
| `run_kpi=True` | user_preferences + analysis_history | Trend awareness, style preferences |
| `run_audit=True` | workspace_context | Previous data knowledge |
| `run_charts=True` | workspace_context | Chart config reuse |
| `run_report=True` | user_preferences + conversation_summary + analysis_history | Full context |
| Any intent | user_preferences | Always (lightweight) |

## MemoryContext Schema

```python
@dataclass
class MemoryContext:
    user_preferences: dict           # {key: value} from user_memories
    workspace_context: dict | None   # last workspace snapshot
    conversation_summary: str        # last 3 conversation snippets
    analysis_history: list[dict]     # last 3 analysis records

    layers_queried: list[str]        # ["user_preferences","analysis_history"]
    total_keys: int                  # for observability

    @property
    def is_empty(self) -> bool:
        return self.total_keys == 0
```

## Feature Flag

```bash
# Enable (router active — selective memory retrieval)
export ENABLE_MEMORY_ROUTER=true

# Disable (default — returns empty MemoryContext)
unset ENABLE_MEMORY_ROUTER
```

## Memory Selection Examples

### User analyzes sales data (`analyze` intent)

```
plan: audit=True, kpi=True, charts=True, report=True
↓
layers: user_preferences, workspace, analysis_history
```

### User requests audit only

```
plan: audit=True, kpi=False, charts=False, report=False
↓
layers: user_preferences, workspace
```

### User requests charts only

```
plan: audit=False, kpi=False, charts=True, report=False
↓
layers: user_preferences, workspace
```

### Router disabled

```
ENABLE_MEMORY_ROUTER not set
↓
MemoryContext(is_empty=True, layers=[])
→ No memory injected, backward compatible
```

## Files

| File | Change |
|------|--------|
| `memory/memory_router.py` | **NEW** — MemoryRouter + MemoryContext (140 lines) |
| `agents/orchestrator.py` | **MODIFIED** — accepts memory_context, injects into prompt |
| `main.py` | **MODIFIED** — wires MemoryRouter into /analyze |

## Verification

```
Routes:            30 loaded
Router OFF:        is_empty=True, 0 layers queried
Router ON:         is_empty=False, 2 layers queried
/analyze:          200 (both modes)
/chat:             200
/export:           200
MemoryContext:     to_dict() works
API compat:        IDENTICAL
Frontend changes:  0
```
