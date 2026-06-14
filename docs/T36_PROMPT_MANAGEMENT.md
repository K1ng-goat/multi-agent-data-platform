# T36 Prompt Management System

> **Date**: 2026-06-04  
> **Endpoints**: `GET /prompts`, `POST /prompts/reload`

---

## Architecture

```
prompt/
├── prompt_manager.py    — load, cache, format(), reload()
├── templates/
│   ├── data_analysis.txt     — AI analysis prompt
│   ├── chat_assistant.txt    — Chat system prompt
│   ├── audit_analysis.txt    — Audit quality prompt
│   ├── report_generation.txt — Report writing prompt
│   └── planner.txt           — Workflow planner prompt
```

## Usage

```python
from prompt.prompt_manager import prompt_manager

# Get raw template
prompt = prompt_manager.get("chat_assistant")

# With format() substitution
prompt = prompt_manager.get("data_analysis",
    filename="sales.xlsx", rows=100, columns=5, ...)
```

## API

```
GET  /prompts        → {"templates": ["audit_analysis","chat_assistant",...]}
POST /prompts/reload  → {"ok": true, "count": 5}
```

## Templates (5)

```
data_analysis     517 chars   Orchestrator AI analysis
chat_assistant     85 chars   Chat system prompt
audit_analysis    280 chars   Data quality auditor
report_generation 320 chars   Report writer
planner           350 chars   Workflow planner
```

## Files

| File | Change |
|------|--------|
| `prompt/__init__.py` | **NEW** |
| `prompt/prompt_manager.py` | **NEW** — PromptManager (55 lines) |
| `prompt/templates/{5 .txt}` | **NEW** — 5 templates |
| `agents/orchestrator.py` | **MODIFIED** — uses template |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T36_PROMPT_MANAGEMENT.md` | Design document |

## Verification

```
Templates:       5
get():            517 chars
reload():         5 (hot reload)
Routes:           41
GET /prompts:     200
POST /reload:     ok
```
