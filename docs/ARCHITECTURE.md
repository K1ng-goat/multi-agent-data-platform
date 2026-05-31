# Multi-Agent Data Platform — Architecture Audit

> **Audit Date**: 2026-05-31  
> **Audit Scope**: Full-stack (backend + frontend + database)  
> **Version**: 0.1.0

---

## 1. Current Tech Stack

### Backend

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Framework | FastAPI | 0.136.3 | REST API, dependency injection, async |
| Server | Uvicorn | 0.48.0 | ASGI process manager |
| Data Analysis | pandas | 3.0.3 | Excel parsing, df.describe(), groupby, Z-score |
| Excel I/O | openpyxl | 3.1.5 | Excel file read/write export |
| Word Export | python-docx | 1.1.2 | Professional Word report generation |
| Chart Export | matplotlib | 3.10.7 | Line/Bar/Pie chart rendering to PNG |
| ORM | SQLAlchemy | 2.0.36 | Declarative ORM, session management |
| Database | SQLite | (built-in) | File-based — `data_agent.db` |
| Auth | python-jose | 3.3.0 | JWT HS256, 7-day expiry |
| Auth | passlib + bcrypt | 1.7.4 / 4.0.1 | Password hashing |
| HTTP Client | httpx | 0.28.1 | Async HTTP → DeepSeek API |
| File Upload | python-multipart | 0.0.29 | FastAPI UploadFile support |
| LLM Provider | DeepSeek API | `deepseek-chat` | Analysis, report, style, chat, function calling |

### Frontend

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Framework | Next.js | 16.2.6 | App Router, Turbopack |
| UI Library | React | 19.2.4 | Client components, hooks |
| Language | TypeScript | 5.x | Type safety |
| Charts | Recharts | 3.8.1 | Line/Bar/Pie interactive charts |
| CSS | Tailwind CSS | 4.x | Utility-first, dark mode |
| State | React Context | — | AuthContext + WorkspaceContext |
| Persistence | localStorage | — | Workspace state + JWT |
| Linter | ESLint | 9.x | eslint-config-next |

---

## 2. Project Directory Structure

```
data-agent/
│
├── backend/
│   ├── main.py                     # FastAPI app — 25+ endpoints (1243 lines)
│   ├── database.py                 # SQLAlchemy engine, SessionLocal, init_db()
│   ├── auth_service.py             # JWT + bcrypt (create_token, hash_password, get_current_user)
│   ├── workflow.py                 # DeepSeek-driven workflow planner + report generator
│   ├── workflow_engine.py          # Multi-Agent orchestration engine (199 lines)
│   ├── export_service.py           # Excel/Word/Chart export
│   ├── dashboard_service.py        # KPI snapshot + dashboard aggregation
│   ├── reports_service.py          # Report history CRUD
│   ├── theme_service.py            # 4-theme system + Chinese natural language style parsing
│   ├── style_config.py             # Live global style configuration module
│   ├── user_model.py               # User ORM model
│   ├── report_model.py             # Report ORM model
│   ├── chat_model.py               # ChatMessage ORM model
│   ├── dashboard_model.py          # DashboardSnapshot ORM model
│   ├── preference_model.py         # UserPreference ORM model
│   ├── requirements.txt            # Python dependencies (12 packages)
│   ├── exports/                    # Generated export files directory
│   │
│   ├── agents/                     # Multi-Agent System (7 agents)
│   │   ├── __init__.py
│   │   ├── base_agent.py           # Abstract BaseAgent class
│   │   ├── data_master_agent.py    # Master orchestrator (149 lines)
│   │   ├── data_agent.py           # Data analysis + DeepSeek AI
│   │   ├── chart_agent.py          # Auto chart generation
│   │   ├── audit_agent.py          # Data quality audit
│   │   ├── report_agent.py         # Report generation via DeepSeek
│   │   ├── style_agent.py          # Theme/style detection + application
│   │   └── export_agent.py         # File export orchestration
│   │
│   └── memory/                     # AI Memory System (4 layers)
│       ├── __init__.py
│       ├── memory_manager.py       # Central orchestrator (singleton)
│       ├── user_memory.py          # User preferences CRUD
│       ├── user_memory_model.py    # UserMemory ORM model
│       ├── workspace_memory.py     # Workspace snapshot CRUD
│       ├── workspace_memory_model.py
│       ├── conversation_memory.py  # Chat history CRUD
│       ├── conversation_memory_model.py
│       ├── longterm_memory.py      # KPI + trend + anomaly storage
│       └── analysis_memory_model.py
│
├── frontend/
│   ├── package.json                # Dependencies (Next.js 16, React 19, Recharts)
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── eslint.config.mjs
│   ├── postcss.config.mjs
│   ├── .gitignore                  # Frontend-specific ignores
│   ├── AGENTS.md / CLAUDE.md       # AI agent instructions
│   ├── public/                     # Static assets
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # Root layout
│       │   ├── globals.css         # Global styles (Tailwind + dark mode)
│       │   ├── page.tsx            # Workspace (main page — upload + chat + charts)
│       │   ├── analytics/page.tsx  # Home/Overview dashboard
│       │   ├── reports/page.tsx    # History center
│       │   ├── memory/page.tsx     # AI memory management
│       │   ├── login/page.tsx      # Login page
│       │   ├── register/page.tsx   # Registration page
│       │   └── components/
│       │       ├── NavBar.tsx         # Navigation bar
│       │       ├── ClientLayout.tsx   # Auth + Workspace providers
│       │       └── ErrorBoundary.tsx  # React error boundary
│       └── lib/
│           ├── api.ts              # apiFetch() wrapper with JWT auto-attach
│           ├── AuthContext.tsx      # Auth state via React Context
│           └── WorkspaceContext.tsx # Workspace state + localStorage persistence
│
├── docs/                           # Documentation (NEW)
├── VERSION.md                      # Version history
├── CHANGELOG.md                    # Changelog
├── ROADMAP.md                      # Project roadmap
├── .gitignore                      # Root gitignore (Python + Node)
└── README.md                       # Project README
```

---

## 3. Agent Architecture

### 3.1 Architecture Diagram

```
                          ┌─────────────────────────────┐
                          │       User Input              │
                          │  (Natural Language Chinese/EN)│
                          └─────────────┬───────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │     /agent-chat Endpoint     │
                          │   (FastAPI → auth → memory)  │
                          └─────────────┬───────────────┘
                                        │
                              ┌─────────┴─────────┐
                              │   Memory Manager   │
                              │  inject context    │
                              └─────────┬─────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │      DataMasterAgent          │
                          │  ┌─────────────────────────┐ │
                          │  │ 1. classify_intent()    │ │
                          │  │    → 8 intent types     │ │
                          │  │ 2. plan_tasks()         │ │
                          │  │    → agent routing map  │ │
                          │  │ 3. execute_pipeline()   │ │
                          │  │    → sequential exec    │ │
                          │  └─────────────────────────┘ │
                          └─────────────┬───────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             │                          │                          │
             ▼                          ▼                          ▼
    ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
    │   Intent:      │        │   Intent:       │        │   Intent:       │
    │   full_report  │        │   analyze       │        │   style         │
    └───────┬────────┘        └───────┬────────┘        └───────┬────────┘
            │                         │                         │
     ┌──────┴──────┐           ┌─────┴─────┐            ┌──────┴──────┐
     │ DataAgent   │           │ DataAgent │            │ StyleAgent  │
     │ AuditAgent  │           └───────────┘            └─────────────┘
     │ ChartAgent  │
     │ ReportAgent │
     │ StyleAgent  │
     │ ExportAgent │
     └─────────────┘
```

### 3.2 Agent Catalog

| # | Agent | Class | File | Role | Key Methods | Dependencies |
|---|-------|-------|------|------|-------------|--------------|
| 0 | **MasterAgent** | `DataMasterAgent` | `data_master_agent.py` | Intent classification, task planning, pipeline orchestration | `classify_intent()`, `plan_tasks()`, `execute_pipeline()` | All 6 sub-agents |
| 1 | **DataAgent** | `DataAgent` | `data_agent.py` | Statistical summary, DeepSeek AI analysis | `summarize()`, `analyze()`, `detect_anomalies()` | pandas, DeepSeek API |
| 2 | **ChartAgent** | `ChartAgent` | `chart_agent.py` | Line/Bar/Pie chart config generation | `generate_charts()` | pandas, `_generate_charts()` |
| 3 | **AuditAgent** | `AuditAgent` | `audit_agent.py` | Data quality audit, Z-score outlier detection | `audit()`, `quality_report()` | pandas |
| 4 | **ReportAgent** | `ReportAgent` | `report_agent.py` | Markdown report via DeepSeek | `generate_report()` | DeepSeek API |
| 5 | **StyleAgent** | `StyleAgent` | `style_agent.py` | Theme detection, style application | `detect_style_intent()`, `apply_style()` | `theme_service` |
| 6 | **ExportAgent** | `ExportAgent` | `export_agent.py` | Excel/Word/Chart file export | `export_excel()`, `export_word()`, `export_chart()` | `export_service` |

### 3.3 Intent Classification Map

```python
INTENT_AGENT_MAP = {
    "analyze":            ["DataAgent"],
    "chart":              ["ChartAgent"],
    "audit":              ["AuditAgent"],
    "report":             ["ReportAgent"],
    "style":              ["StyleAgent"],
    "export":             ["ExportAgent"],
    "full_report":        ["DataAgent", "AuditAgent", "ChartAgent", "ReportAgent", "StyleAgent", "ExportAgent"],
    "data_with_charts":   ["DataAgent", "ChartAgent"],
    "analyze_and_report": ["DataAgent", "ReportAgent"],
}
```

### 3.4 Shared Context Flow

All agents share a single Python `dict` that flows through the pipeline:

```python
context = {
    "session_id": str,          # UUID session identifier
    "user_message": str,        # Raw user input (+ memory context prepended)
    "intent": str,              # Classified intent
    "df": pd.DataFrame | None,  # Uploaded Excel data
    "data_summary": dict,       # {filename, shape, columns, dtypes, describe, sample, null_counts}
    "analysis": dict | None,    # {summary, anomaly, trend}
    "charts": list | None,      # [{type, title, labels, datasets}]
    "audit_result": dict | None,# {null_report, duplicate_count, outlier_count, quality_score}
    "style": dict | None,       # {theme, overrides}
    "report": str | None,       # Generated markdown report
    "exports": list | None,     # [{type, filename}]
    "steps": list,              # [{agent, status, message}] — frontend visualization
    "errors": list,             # Collected error strings
    "api_key": str,             # DeepSeek API key
    "memory_context": str,      # RAG-injected memory context
    "active_theme": str,        # "business" | "simple" | "dark" | "academic"
    "style_overrides": dict,    # Per-session style overrides
}
```

**Safety**: Before returning to frontend, `workflow_engine.format_response()` strips `df` and `_df` from context (DataFrame is not JSON-serializable). Response is hard-capped at 500KB.

---

## 4. Memory Architecture (RAG)

### 4.1 Four-Layer Design

```
┌─────────────────────────────────────────────────────┐
│                  MemoryManager                       │
│                  (Singleton)                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐  ┌─────────────────┐           │
│  │  Layer 1:        │  │  Layer 2:        │          │
│  │  User Memory     │  │  Workspace       │          │
│  │  ─────────────   │  │  Memory          │          │
│  │  • Preferences   │  │  ─────────────   │          │
│  │  • Key-value     │  │  • Snapshots     │          │
│  │  • Per-user      │  │  • Data + Charts │          │
│  │  • Category tag  │  │  • Session-based │          │
│  │  Table:           │  │  Table:           │         │
│  │  user_memories   │  │  workspace_mem.. │          │
│  └────────┬────────┘  └────────┬────────┘           │
│           │                    │                     │
│  ┌────────┴────────┐  ┌────────┴────────┐           │
│  │  Layer 3:        │  │  Layer 4:        │          │
│  │  Conversation    │  │  Long-term       │          │
│  │  Memory          │  │  Analysis Memory │          │
│  │  ─────────────   │  │  ─────────────   │          │
│  │  • Chat history  │  │  • KPI snapshots │          │
│  │  • Per-session   │  │  • Trend/Anomaly │          │
│  │  • Role+Mode     │  │  • Full reports  │          │
│  │  Table:           │  │  • Keyword search│         │
│  │  conversation_.. │  │  Table:           │         │
│  └─────────────────┘  │  analysis_memo.. │          │
│                       └─────────────────┘           │
└─────────────────────────────────────────────────────┘
```

### 4.2 Memory Retrieval Flow

```
User sends message
        │
        ▼
/agent-chat → MemoryManager.retrieve_relevant_memories()
        │
        ├─→ Layer 1: get_user_preferences(user_id)
        │      → {key: value, ...}
        │
        ├─→ Layer 2: get_workspace(user_id, session_id)
        │      → {filename, data_summary, charts_summary, analysis_summary}
        │
        ├─→ Layer 3: get_conversation_history(user_id, session_id)
        │      → [{role, content, mode, ...}, ...] (last 5)
        │
        └─→ Layer 4: search_similar_analyses(user_id, keyword)
               → [{kpi, trend, anomaly, report_content, ...}] (keyword match)
        │
        ▼
MemoryManager.build_memory_prompt(memories)
        → "[用户偏好]\nkey=value\n\n[历史分析文件]\nfile1, file2\n\n[最近对话]\n..."
        │
        ▼
Injected into context["user_message"] as prefix
```

---

## 5. Data Flow Diagram

### 5.1 Upload → Analysis → Display

```
Browser                     FastAPI                        DeepSeek API
  │                           │                                │
  │ POST /analyze + file      │                                │
  ├──────────────────────────►│                                │
  │                           │ pandas.read_excel()            │
  │                           │ _convert_excel_dates()         │
  │                           │ _generate_charts()             │
  │                           │                                │
  │                           │ POST /chat/completions         │
  │                           ├───────────────────────────────►│
  │                           │                                │
  │                           │ ◄─────────────────────────────│
  │                           │ {summary, anomaly, trend}      │
  │                           │                                │
  │                           │ ds.update_snapshot()    (SQLite)
  │                           │ rs.save_report()        (SQLite)
  │                           │ mgr.save_workspace()    (Memory)
  │                           │ mgr.save_analysis()     (Memory)
  │                           │                                │
  │ {session_id, charts,      │                                │
  │  data_summary, analysis}  │                                │
  │◄──────────────────────────│                                │
  │                           │                                │
  │ Render: Recharts +        │                                │
  │ Analysis text + KPI cards │                                │
```

### 5.2 Chat → Flow

```
Browser                     FastAPI                        DeepSeek API
  │                           │                                │
  │ POST /chat                │                                │
  ├──────────────────────────►│                                │
  │                           │ _classify_intent()             │
  │                           │                                │
  │                   ┌───────┴────────┐                       │
  │                   │                │                       │
  │              intent=c          intent=w                     │
  │                   │                │                       │
  │           CHAT MODE          WORKFLOW MODE                  │
  │                   │                │                       │
  │           POST tools       wf.plan_workflow()               │
  │           (up to 3x)           │                            │
  │                   │         _execute_tool() × N             │
  │                   │            │                            │
  │                   │         wf.generate_report()            │
  │                   │            │                            │
  │                   ▼            ▼                            │
  │              ┌─────────────────┘                            │
  │              │ POST /chat/completions                       │
  │              ├─────────────────────────────────────────────►│
  │              │                                              │
  │              │◄─────────────────────────────────────────────│
  │              │                                              │
  │ {reply,       │                                              │
  │  steps,       │                                              │
  │  plan/timeline}│                                             │
  │◄──────────────│                                              │
```

### 5.3 Agent Chat → Flow

```
POST /agent-chat
    │
    ├── 1. MemoryManager.retrieve_relevant_memories()
    │      └── Build memory context prompt
    │
    ├── 2. _persist_chat() → ChatMessage (SQLite)
    │
    ├── 3. WorkflowEngine.run()
    │      │
    │      ├── create_context()
    │      ├── DataMasterAgent.execute()
    │      │   ├── classify_intent()
    │      │   ├── plan_tasks()
    │      │   └── execute_pipeline()
    │      │       ├── DataAgent.execute()
    │      │       ├── AuditAgent.execute()
    │      │       ├── ChartAgent.execute()
    │      │       ├── ReportAgent.execute()
    │      │       ├── StyleAgent.execute()
    │      │       └── ExportAgent.execute()
    │      │
    │      ├── context.pop("df")  ← SAFETY: strip DataFrame
    │      └── format_response()
    │          └── 500KB hard limit check
    │
    └── 4. Return to browser
```

---

## 6. API Inventory (25 endpoints)

### 6.1 Authentication (3)

| # | Method | Endpoint | Auth | Input | Output |
|---|--------|----------|------|-------|--------|
| 1 | `POST` | `/register` | No | `{username, email, password}` | `{access_token, user}` |
| 2 | `POST` | `/login` | No | `{email, password}` | `{access_token, user}` |
| 3 | `GET` | `/me` | Yes | — | `{id, username, email, created_at}` |

### 6.2 Core Analysis (4)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 4 | `POST` | `/upload` | No | Upload Excel → raw data (no AI) |
| 5 | `POST` | `/analyze` | Yes | Upload + full AI analysis + charts |
| 6 | `POST` | `/chat` | Yes | Chat with function calling (6 tools) |
| 7 | `POST` | `/agent-chat` | Yes | Multi-Agent pipeline chat |

### 6.3 Workflow (1)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 8 | `POST` | `/workflow` | No | Plan → Execute → Report (no auth) |

### 6.4 Dashboard & Reports (3)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 9 | `GET` | `/dashboard` | Yes | KPI cards + charts + AI summary |
| 10 | `GET` | `/reports` | Yes | List historical reports |
| 11 | `GET` | `/reports/{id}` | Yes | Get single report detail |

### 6.5 Memory System (7)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 12 | `GET` | `/memory/preferences` | Yes | Get user preferences |
| 13 | `POST` | `/memory/preferences` | Yes | Save preference |
| 14 | `DELETE` | `/memory/preferences` | Yes | Delete preference by key |
| 15 | `GET` | `/memory/recent` | Yes | Recent analyses + workspaces |
| 16 | `GET` | `/memory/conversations/{id}` | Yes | Conversation history |
| 17 | `GET` | `/memory/retrieve` | Yes | Retrieve memory context |
| 18 | `GET` | `/memory/summary` | Yes | Aggregated memory stats |
| 19 | `POST` | `/memory/clear` | Yes | Clear memory by type |

### 6.6 Style & Theme (3)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 20 | `GET` | `/themes` | No | List 4 preset themes |
| 21 | `POST` | `/style/apply` | Yes | Apply theme to session |
| 22 | `GET` | `/style/preview/{id}` | Yes | Preview style config |

### 6.7 Export (3)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 23 | `GET` | `/export/excel/{id}` | No | Download Excel (.xlsx) |
| 24 | `GET` | `/export/word/{id}` | No | Download Word (.docx) |
| 25 | `GET` | `/export/chart/{id}/{idx}` | No | Download Chart (.png) |

### 6.8 Health Check (1)

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 0 | `GET` | `/` | No | `{"message": "AI Excel Data Agent API is running"}` |

---

## 7. Database Schema (9 tables)

### 7.1 Table Inventory

```
data_agent.db
├── users                        # User accounts
├── chat_messages                # Per-session chat history
├── dashboard_snapshots          # Latest analysis KPIs per user
├── user_preferences             # Global style preferences
├── reports                      # Saved analysis reports
├── user_memories                # Memory Layer 1: User preferences (key-value)
├── workspace_memories           # Memory Layer 2: Workspace snapshots
├── conversation_memories        # Memory Layer 3: Conversation history
└── analysis_memories            # Memory Layer 4: Long-term analysis
```

### 7.2 Column Breakdown

**users**
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `username` | VARCHAR | unique |
| `email` | VARCHAR | unique |
| `password_hash` | VARCHAR | bcrypt |
| `created_at` | VARCHAR | ISO datetime string |

**chat_messages**
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `session_id` | VARCHAR | indexed |
| `user_id` | INTEGER | FK→users |
| `role` | VARCHAR | "user" / "assistant" |
| `content` | TEXT | full message text |
| `created_at` | VARCHAR | ISO datetime |

**dashboard_snapshots**
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `session_id` | VARCHAR | unique per user |
| `user_id` | INTEGER | FK→users |
| `filename` | VARCHAR | Excel filename |
| `rows` | INTEGER | data rows |
| `columns` | INTEGER | data columns |
| `kpi` | TEXT | JSON array |
| `charts` | TEXT | JSON array |
| `ai_summary` | TEXT | analysis summary |
| `ai_trend` | TEXT | trend analysis |
| `ai_anomaly` | TEXT | anomaly detection |
| `columns_list` | TEXT | JSON array |
| `updated_at` | VARCHAR | ISO datetime |

**user_preferences**
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `user_id` | INTEGER | FK→users |
| `key` | VARCHAR | e.g. "active_theme" |
| `value` | TEXT | JSON value |

**reports** (same structure as dashboard_snapshots)

**user_memories** (Memory Layer 1)
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `user_id` | INTEGER | FK→users |
| `category` | VARCHAR | "preference" / "behavior" / "analysis" / "export" / "style" |
| `key` | VARCHAR | preference key |
| `value` | TEXT | preference value |
| `updated_at` | VARCHAR | ISO datetime |

**workspace_memories** (Memory Layer 2)
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `user_id` | INTEGER | FK→users |
| `session_id` | VARCHAR | unique per user |
| `filename` | VARCHAR | Excel filename |
| `data_summary` | TEXT | JSON summary |
| `charts_summary` | TEXT | JSON charts |
| `analysis_summary` | TEXT | JSON analysis |
| `active_theme` | VARCHAR | "business"/"simple"/"dark"/"academic" |
| `created_at` | VARCHAR | ISO datetime |
| `updated_at` | VARCHAR | ISO datetime |

**conversation_memories** (Memory Layer 3)
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `user_id` | INTEGER | FK→users |
| `session_id` | VARCHAR | indexed |
| `role` | VARCHAR | "user" / "ai" |
| `content` | TEXT | message text |
| `mode` | VARCHAR | "chat" / "workflow" / "agent" |
| `steps_json` | TEXT | JSON steps |
| `created_at` | VARCHAR | ISO datetime |

**analysis_memories** (Memory Layer 4)
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | auto-increment |
| `user_id` | INTEGER | FK→users |
| `session_id` | VARCHAR | indexed |
| `filename` | VARCHAR | Excel filename |
| `kpi_json` | TEXT | JSON KPI data |
| `trend_json` | TEXT | JSON trend |
| `anomaly_json` | TEXT | JSON anomaly |
| `report_content` | TEXT | full report markdown |
| `created_at` | VARCHAR | ISO datetime |

### 7.3 Schema Anti-Patterns

| Issue | Location | Severity |
|-------|----------|----------|
| **No foreign key constraints** | All FK columns (user_id, session_id) | HIGH — SQLite FK enforcement off by default, referential integrity not guaranteed |
| **Datetime stored as VARCHAR** | All `created_at`, `updated_at` columns | MEDIUM — cannot use SQL date functions; relies on app-layer formatting |
| **JSON stored as TEXT** | `kpi`, `charts`, `kpi_json`, `data_summary`, `steps_json` | MEDIUM — no JSON validation at DB level |
| **Duplicate tables** | `user_preferences` vs `user_memories (category="preference")` | HIGH — two systems storing preferences in parallel |
| **No indexes on FK columns** | `user_id`, `session_id` across all tables | LOW — performance will degrade with growth |
| **`dashboard_snapshots` ≈ `reports`** | Nearly identical schema | MEDIUM — functional overlap |

---

## 8. Technical Debt

### 8.1 Critical (Must Fix)

| # | Issue | Location | Impact | Fix Effort |
|---|-------|----------|--------|------------|
| T1 | **In-memory session store** — all sessions lost on restart | `main.py:L47` `sessions: dict` | Users lose work on server restart | HIGH — migrate to SQLite/Redis |
| T2 | **No foreign key enforcement** | All models | Orphaned records, referential corruption | Medium — add `ForeignKey` + PRAGMA |
| T3 | **Duplicate auth: `/workflow` has no auth** while `/chat` does | `main.py:L732` vs `L802` | Unauthenticated workflow execution | Low — add `Depends(get_current_user)` |
| T4 | **No input validation on file upload** — any file accepted | `main.py:L345` `upload_excel` | Crash on non-Excel files | Low — add file extension/magic byte check |
| T5 | **SQLite single-threaded access** with `check_same_thread=False` | `database.py:L8` | Potential data corruption under concurrent access | Medium — switch to WAL mode + connection pooling |

### 8.2 High

| # | Issue | Location | Impact | Fix Effort |
|---|-------|----------|--------|------------|
| T6 | **Two parallel intent classifiers** — `_classify_intent()` in main.py + `DataMasterAgent.classify_intent()` | `main.py:L103` + `data_master_agent.py:L86` | Divergent behavior, maintenance burden | Medium — consolidate |
| T7 | **Two parallel preference systems** — `user_preferences` table + `user_memories (category=preference)` | `preference_model.py` + `user_memory.py` | Data duplication, confusion | Medium — merge into one |
| T8 | **No API versioning** — all endpoints unversioned | All 25 endpoints | Breaking changes impossible to roll out | Low — prefix with `/api/v1/` |
| T9 | **No rate limiting** | All endpoints | LLM API abuse risk | Low — add slowapi / Redis rate limiter |
| T10 | **No request body size limit** for `/analyze` | `main.py:L451` | Memory exhaustion on large files | Low — add Content-Length check |

### 8.3 Medium

| # | Issue | Location | Impact | Fix Effort |
|---|-------|----------|--------|------------|
| T11 | **`dashboard_snapshots` ≈ `reports`** — redundant schema | `dashboard_model.py` + `report_model.py` | Double writes, storage waste | Medium — consolidate into one |
| T12 | **DeepSeek API key checked inline** — no config module | Scattered across `main.py` | Hard to change provider | Medium — extract `config.py` |
| T13 | **No structured logging** — all `print()` | All backend files | No log levels, hard to debug in production | Medium — introduce `logging` module |
| T14 | **No automated tests** | Entire project | Regression risk | HIGH effort — add pytest |
| T15 | **Mixed Chinese/English in code** | `main.py` prompts, comments | Readability for non-Chinese developers | Low — extract i18n strings |

### 8.4 Low

| # | Issue | Location | Impact | Fix Effort |
|---|-------|----------|--------|------------|
| T16 | **Frontend: single-file `page.tsx` with 50+ sub-components** | `frontend/src/app/page.tsx` | Hard to navigate, large file | Medium — split into component files |
| T17 | **No TypeScript strict mode** | `tsconfig.json` | Missing type errors | Low — enable `strict: true` |
| T18 | **No `.env.example`** | Root | New developers don't know required env vars | Low — create file |
| T19 | **Hardcoded localhost URLs** in frontend API calls | All frontend pages | Cannot deploy to different hosts | Medium — use env variable |
| T20 | **No data migration strategy** | `database.py:init_db()` | Schema changes will orphan existing data | Medium — add Alembic |

---

## 9. Next-Stage Optimization Recommendations

### Phase 1: Reliability (v0.2.0) — 2-3 weeks

| Priority | Task | Rationale |
|----------|------|-----------|
| **P0** | Add automated tests (pytest for backend, Vitest for frontend) | Zero tests = zero confidence in changes |
| **P0** | Migrate sessions to DB-backed storage | Server restart wipes all user work |
| **P0** | Enable SQLite WAL mode + add FK constraints | Data integrity |
| **P1** | Consolidate `user_preferences` ↔ `user_memories` | Stop writing to two systems |
| **P1** | Consolidate intent classifiers | Single source of truth |
| **P1** | Add input validation to `/upload` | Crash prevention |
| **P1** | Create `config.py` + `.env.example` | Clean configuration |
| **P2** | Replace `print()` with structured `logging` | Debuggability |
| **P2** | Add API versioning (`/api/v1/`) | Future-proofing |

### Phase 2: Architecture (v0.3.0) — 2-3 weeks

| Priority | Task | Rationale |
|----------|------|-----------|
| **P0** | Split `page.tsx` into component files | Maintainability |
| **P1** | Add Alembic for schema migrations | Safe schema evolution |
| **P1** | Consolidate `dashboard_snapshots` + `reports` | Remove redundancy |
| **P1** | Enable TypeScript `strict: true` | Catch type errors early |
| **P2** | Extract API base URL to env variable | Deploy flexibility |
| **P2** | Add rate limiting for `/chat` and `/agent-chat` | LLM cost control |

### Phase 3: Production Readiness (v0.4.0) — 3-4 weeks

| Priority | Task | Rationale |
|----------|------|-----------|
| **P0** | Add proper error responses (HTTP status codes) | Current: many return `{"error": "..."}` with 200 |
| **P1** | Add request/response compression (gzip) | Reduce bandwidth |
| **P1** | Add async background task for LLM calls | Non-blocking user experience |
| **P1** | Add streaming response for `/chat` (SSE) | Real-time UX |
| **P2** | Implement agent execution parallelism | Speed (currently sequential only) |
| **P2** | Add proper CORS configuration for production | Security |
| **P2** | Docker containerization | Deploy reproducibility |

### Phase 4: Scale (v0.5.0+) — Future

| Task | Rationale |
|------|-----------|
| Redis for caching + session store | Performance under load |
| PostgreSQL migration for concurrency | Scale beyond SQLite |
| Multi-model LLM support (Claude, GPT) | Provider flexibility |
| Real-time collaboration (WebSocket) | Multi-user editing |
| Plugin system for custom agents | Extensibility |

---

## Appendix A: File Size Overview

| File | Lines | Description |
|------|-------|-------------|
| `backend/main.py` | 1243 | FastAPI app — largest single file |
| `frontend/src/app/page.tsx` | ~900 | Main workspace page |
| `backend/workflow_engine.py` | 199 | Agent orchestration engine |
| `backend/agents/data_master_agent.py` | 149 | Master agent |
| `backend/theme_service.py` | ~400 | Theme/style system |
| `backend/export_service.py` | ~300 | File export |

## Appendix B: CORS Configuration

```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d{4}$"
```

**Note**: CORS currently allows ANY localhost port. Tighten for production.

## Appendix C: DeepSeek API Usage

| Endpoint | Model | Temperature | Max Rounds | Purpose |
|----------|-------|-------------|------------|---------|
| `/analyze` | `deepseek-chat` | 0.7 | 1 | Initial analysis |
| `/chat` (first call) | `deepseek-chat` | 0.3 | 1 | Tool-selection |
| `/chat` (subsequent) | `deepseek-chat` | 0.7 | 3 | Follow-up analysis |
| Workflow plan | `deepseek-chat` | 0.2 | 1 | Structured plan JSON |
| Workflow report | `deepseek-chat` | 0.5 | 1 | Final report |
| Style parsing | `deepseek-chat` | 0.1 | 1 | Style parameter extraction |
| Agent analysis | `deepseek-chat` | 0.7 | 1 | Per-agent AI work |
