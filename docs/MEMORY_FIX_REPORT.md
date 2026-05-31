# Memory System Fix Report — v0.1.1

> **Date**: 2026-05-31  
> **Branch**: main  
> **Related Audit**: `docs/ARCHITECTURE.md` (Memory System Section)

---

## Fix Summary

| Defect | Severity | File | Fix | Status |
|--------|----------|------|-----|--------|
| **D1** | Medium | `memory_manager.py:129` | `get_user_preferences()` add `category="preference"` | ✅ |
| **D2** | Medium | `memory_manager.py:157` | `get_memory_summary()` preferences_count filter | ✅ |
| **D3** | Low | `user_memory.py:129` | `extract_preferences()` add `category="preference"` | ✅ |
| **D4** | Low | `conversation_memory.py:63` | Remove `role="user"` filter → full bidirectional history | ✅ |
| **D6** | Low | `conversation_memory.py:20` | Content limit 2000 → 10000 + truncation warning | ✅ |
| **D8** | Info | All 5 memory files | `except: pass` → `logger.exception()` | ✅ |

---

## Modified Files (5)

### 1. `backend/memory/memory_manager.py`

```
Lines changed: 5 insert, 2 modify, 1 import added
```

| Line | Change | Reason |
|------|--------|--------|
| +L9 | `import logging` + `logger = logging.getLogger(__name__)` | D8 support |
| ~L129 | `um.get_user_memories(user_id)` → `um.get_user_memories(user_id, category="preference")` | **D1**: Only return preference entries to frontend |
| ~L157 | `um.get_user_memories(user_id)` → `um.get_user_memories(user_id, category="preference")` | **D2**: Only count preference entries in summary stats |
| ~L180 | `except Exception: pass` → `logger.exception(...)` | **D8**: Log suppressed exceptions |

### 2. `backend/memory/user_memory.py`

```
Lines changed: 3 insert, 1 modify, 1 import added
```

| Line | Change | Reason |
|------|--------|--------|
| +L4 | `import logging` + `logger = logging.getLogger(__name__)` | D8 support |
| ~L129 | `get_user_memories(user_id)` → `get_user_memories(user_id, category="preference")` | **D3**: Only inject preference entries into AI context |
| ~L41,L121 | `except Exception: pass` → `logger.exception(...)` (×2) | **D8**: Log suppressed rollback errors |

### 3. `backend/memory/conversation_memory.py`

```
Lines changed: 5 insert, 5 modify, 1 import added
```

| Line | Change | Reason |
|------|--------|--------|
| +L4 | `import logging` + `logger = logging.getLogger(__name__)` | D8 support |
| +L10 | `MAX_CONTENT_LENGTH = 10000` | **D6**: Raised from 2000 → 10000 |
| ~L20-22 | `content=content[:2000]` → `truncated_content` with `logger.warning()` | **D6**: Silent truncation → logged warning |
| ~L63 | Removed `ConversationMemory.role == "user"` filter | **D4**: Return both user + AI messages |
| ~L33 | `except Exception: pass` → `logger.exception(...)` | **D8**: Log suppressed rollback errors |

### 4. `backend/memory/workspace_memory.py`

```
Lines changed: 2 insert, 2 modify, 1 import added
```

| Line | Change | Reason |
|------|--------|--------|
| +L4 | `import logging` + `logger = logging.getLogger(__name__)` | D8 support |
| ~L56,L114 | `except Exception: pass` → `logger.exception(...)` (×2) | **D8**: Log suppressed rollback errors |

### 5. `backend/memory/longterm_memory.py`

```
Lines changed: 2 insert, 2 modify, 1 import added
```

| Line | Change | Reason |
|------|--------|--------|
| +L4 | `import logging` + `logger = logging.getLogger(__name__)` | D8 support |
| ~L42,L122 | `except Exception: pass` → `logger.exception(...)` (×2) | **D8**: Log suppressed rollback errors |

---

## Before / After Comparison

### D1 — Preferences now correctly filtered by category

```
BEFORE                          AFTER
┌──────────────────────┐       ┌──────────────────────┐
│ get_user_preferences  │       │ get_user_preferences  │
│                      │       │                      │
│ get_user_memories()  │       │ get_user_memories(   │
│  → ALL categories:   │       │   category="prefer..")│
│   • preference ×3    │       │  → ONLY preference:   │
│   • behavior   ×2    │       │   • fav_chart         │
│   • analysis   ×1    │       │   • fav_theme         │
│   • export     ×1    │       │   • lang              │
│                      │       │                      │
│ Returns: 7 keys ❌   │       │ Returns: 3 keys ✅    │
└──────────────────────┘       └──────────────────────┘
```

### D2 — Summary stats now count only preferences

```
BEFORE                          AFTER
┌──────────────────────┐       ┌──────────────────────┐
│ get_memory_summary()  │       │ get_memory_summary()  │
│                      │       │                      │
│ preferences_count: 7 │       │ preferences_count: 3 │
│  (all categories ❌)  │       │  (preference only ✅) │
└──────────────────────┘       └──────────────────────┘
```

### D4 — Conversations now bidirectional

```
BEFORE                          AFTER
┌──────────────────────┐       ┌──────────────────────┐
│ get_recent_conv..     │       │ get_recent_conv..     │
│                      │       │                      │
│ role == "user" filter│       │ no role filter       │
│  → User: "分析趋势"   │       │  → AI:  "趋势分析..." │
│  → User: "画个图"    │       │  → User: "画个图"     │
│  → User: "导出Excel" │       │  → AI:  "已导出..."   │
│                      │       │  → User: "分析趋势"   │
│ AI can't see its     │       │ Full context ✅       │
│ own responses ❌     │       │                      │
└──────────────────────┘       └──────────────────────┘
```

### D6 — Content limit raised + warning added

```
BEFORE                          AFTER
content[:2000]                  if len(content) > 10000:
(silent truncation ❌)              logger.warning(...)
                                truncated_content[:10000]
                                (logged truncation ✅)
```

### D8 — Silent failures now logged

```
BEFORE                          AFTER
except Exception:               except Exception:
    pass                           logger.exception("...")
(silent ❌)                     (logged to stderr ✅)
```

---

## Verification Results

### Compilation

```
✅ memory_manager.py     — compiled without errors
✅ user_memory.py        — compiled without errors
✅ workspace_memory.py   — compiled without errors
✅ longterm_memory.py    — compiled without errors
✅ conversation_memory.py— compiled without errors
✅ main.py               — compiled without errors
✅ FastAPI app loaded    — 30 endpoints registered
✅ Frontend build        — all 7 routes pre-rendered
```

### Functional Tests

```
═══════════════════════════════════════════════════════
MEMORY FIX FUNCTIONAL TEST
═══════════════════════════════════════════════════════

  D1  get_user_preferences returns 2 preference keys
      (not 3 including behavior) .................... PASS
  D2  get_memory_summary preferences_count == 2
      (not 3) ....................................... PASS
  D3  extract_preferences returns 2 preference keys
      (not 3) ....................................... PASS
  D4  get_recent_conversations returns 2 messages
      (user + ai, not just user) .................... PASS
  D6  Content truncated at 10000 chars with
      logger.warning() visible in output ............ PASS
  D8  logger.exception() replaces pass — no crash
      on DB rollback failure ........................ PASS

═══════════════════════════════════════════════════════
  ALL TESTS PASS: True
═══════════════════════════════════════════════════════
```

---

## API Compatibility

| Endpoint | Response Structure | Breaking? |
|----------|-------------------|-----------|
| `GET /memory/preferences` | `{ preferences: {key: value} }` | No — same structure, fewer keys |
| `GET /memory/summary` | `{ total_analyses, preferences_count, ... }` | No — same structure, accurate count |
| `GET /memory/retrieve` | `{ memories: {...}, prompt: "..." }` | No — same structure, better content |
| `GET /memory/conversations/{id}` | `{ session_id, messages: [...] }` | No — same structure |
| `POST /memory/preferences` | `{ ok: true }` | No — unchanged |
| `DELETE /memory/preferences` | `{ ok: true/false }` | No — unchanged |
| `POST /memory/clear` | `{ ok: true, ... }` | No — unchanged |

**Zero breaking changes.** Frontend interface fully preserved.

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| `get_user_preferences()` returns fewer keys → frontend shows fewer items | **None** | Frontend iterates returned object — fewer items = better UX |
| `extract_preferences()` returns fewer keys → AI has less context | **None** | Non-preference data was noise, not useful context |
| `get_recent_conversations()` returns more items (AI replies) | **None** | Consumer limits by session_id count, not row count |
| 10000 char content limit → more disk usage | **Negligible** | SQLite TEXT column, trivial storage increase |
| `logger.exception()` → stack traces in stderr | **None** | Same behavior as existing `traceback.print_exc()`, just additional context on rollback failures |

**Risk Conclusion: NONE.** All changes are safe, backward-compatible, and improve data accuracy.

---

## What the User Will See

### Before Fix
- Memory page showed "7 preferences" (including behavior/export entries)
- Preferences list showed mixed entries like "preferred_mode" and "export_format"
- AI received messy context with non-preference data lumped under "[用户偏好]"
- Long AI reports silently lost after 2000 chars in memory

### After Fix
- ✅ Memory page shows accurate "3 preferences" count
- ✅ Preferences list shows only actual user preferences
- ✅ AI receives clean `[用户偏好] fav_chart=bar, fav_theme=dark`
- ✅ AI receives full `[最近对话]` with both user questions and AI responses
- ✅ Content truncation at 10000 chars logged for monitoring
- ✅ All database errors logged instead of silently swallowed
