# T44 Redis Cache Layer

> **Date**: 2026-06-04  
> **Endpoints**: `GET /cache/stats`, `POST /cache/clear`  
> **Feature Flag**: `ENABLE_REDIS_CACHE=true`

---

## Architecture

```
                  ┌─────────────────┐
                  │   Cache Manager  │
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         Knowledge      Prompt       Agent
         Retriever      Manager      Outputs
         (T43)          (T36)        (T23)

         Redis (ENABLE_REDIS_CACHE=true)
                ↓ failure
         In-memory fallback (always works)
```

## Cache Flow

```
retriever.search("roe")
  ↓
cache.make_key("knowledge", "roe", "3")
  ↓
cache.get(key) → HIT? → return cached
               → MISS? → KnowledgeBase.search() → cache.set(key, result, ttl=3600)
```

## Feature Flag

```bash
ENABLE_REDIS_CACHE=true   # Redis active (if REDIS_URL set)
ENABLE_REDIS_CACHE=false  # Bypass cache (default)
```

Redis unavailable? In-memory fallback takes over. System never breaks.

## API

```
GET  /cache/stats   → {"hits":2, "misses":1, "hit_rate":66.7, "backend":"memory"}
POST /cache/clear   → {"ok":true}
```

## Cache Keys

```python
cache.make_key("knowledge", query, str(top_k))
# → "knowledge:d5d70cbb4bb8bde0"
```

## Files

| File | Change |
|------|--------|
| `cache_manager.py` | **NEW** — CacheManager (110 lines) |
| `knowledge/retriever.py` | **MODIFIED** — search() uses cache |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T44_REDIS_CACHE_LAYER.md` | Design document |

## Verification

```
get/set:           OK
TTL expire:        OK
Knowledge cache:   hits=2 (second search("roe") hit cache)
/analyze:          200
Routes:            57
Redis unavailable: graceful fallback to memory
```