# T37 Memory Compression Layer

> **Date**: 2026-06-04  
> **Endpoints**: `GET /memory/compressed`, `POST /memory/compress`

---

## Architecture

```
Conversation Memory (100 items)      Analysis Memory (100 items)
  ↓                                     ↓
MemoryCompressor.compress()            MemoryCompressor.compress()
  ↓                                     ↓
Summary (topics)                       Summary (findings)
  ↓                                     ↓
compressed_memories table              compressed_memories table
```

## ORM Model

```sql
compressed_memories:
  id, user_id, memory_type, summary(2000),
  item_count, compressed_count, created_at
```

## API

```
GET  /memory/compressed    → compressed summaries for user
POST /memory/compress       → trigger compression run
```

## Files

| File | Change |
|------|--------|
| `memory/compressed_memory.py` | **NEW** — ORM model (14 lines) |
| `memory/memory_compressor.py` | **NEW** — MemoryCompressor (85 lines) |
| `database.py` | **MODIFIED** — registers compressed_memories |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T37_MEMORY_COMPRESSION.md` | Design document |

## Verification

```
compress():       analysis: 3 items → 319 chars
get_compressed:   1 entry
POST /compress:   ok
GET /compressed:  200
Routes:           43 (41 + 2 compression)
```
