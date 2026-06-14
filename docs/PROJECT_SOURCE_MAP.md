# Project Source Map

> **Files**: 97 | **Total Size**: 384 KB | **Backend**: Python 3.11 + FastAPI | **Frontend**: Next.js 16 + React 19

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Next.js 16, React 19, Recharts, Tailwind CSS)    │
│  /  /analytics  /reports  /memory  /playground  /dashboard │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (JWT Bearer)
┌──────────────────────▼──────────────────────────────────────┐
│  FastAPI (main.py — 54KB, 55 routes)                       │
│                                                             │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │ Agent Layer │ │ Memory Layer │ │ Infrastructure   │     │
│  │ (T22-T32)   │ │ (D1-T25)     │ │ (T1-T21)         │     │
│  └──────┬──────┘ └──────┬───────┘ └────────┬─────────┘     │
│         │               │                   │               │
│  ┌──────▼───────────────▼───────────────────▼─────────┐     │
│  │          LLM / Knowledge / Tools / Prompt          │     │
│  │          (T34-T39, T43-T44)                        │     │
│  └──────────────────────┬─────────────────────────────┘     │
│                         │                                    │
│  ┌──────────────────────▼─────────────────────────────┐     │
│  │     SQLite / SessionStore / parquet files           │     │
│  │     11 tables, WAL mode, FK pragma                  │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Request Flow Diagrams

### /analyze (Upload + Analysis)

```
Browser POST /analyze + file.xlsx
  ↓
_validate_excel_upload()          main.py     [T4]
  ↓
memory_router.route()             memory_router.py  [T25]
  ↓
orchestrator.run_analysis_pipeline()  orchestrator.py  [T23]
  ├── pd.read_excel()
  ├── _convert_excel_dates()
  ├── planner.plan()              planner_agent.py  [T24]
  ├── retriever.retrieve_for_prompt()  retriever.py  [T43]
  ├── _generate_charts()
  ├── _ai_analyze()               (DeepSeek API)
  ├── _persist_dashboard()        dashboard_service.py
  ├── _persist_memory()           memory_manager.py
  ├── session_store.save()        session_store.py  [T1]
  └── trace_store.save()          workflow_trace.py  [T30]
  ↓
{ session_id, data_summary, charts, analysis }
```

### /chat (Conversation)

```
Browser POST /chat {session_id, question}
  ↓
_get_session()                     main.py     [T1]
  ↓
ChatOrchestrator.execute()        chat_orchestrator.py  [T31]
  ├── classify_for_chat()         intent_classifier.py  [T6]
  ├── DeepSeek API (tool-calling, 6 tools, max 3 rounds)
  ├── trace_store.save()          workflow_trace.py  [T30]
  └── metrics_registry.record()   metrics.py  [T28]
  ↓
{ mode, reply, steps }
```

### /agent-chat (Multi-Agent Pipeline)

```
Browser POST /agent-chat
  ↓
MemoryManager.retrieve_relevant_memories()  [Memory]
  ↓
WorkflowEngine.run()               workflow_engine.py
  ↓
DataMasterAgent.execute()          data_master_agent.py
  ├── classify()                   intent_classifier.py
  ├── plan_tasks()                 → registry.get_intent_agents()
  └── execute_pipeline()           → ParallelExecutionManager [T32]
       ├── [DataAgent]             → safe_execute() [T26]
       ├── [AuditAgent, ChartAgent] → parallel [T32]
       └── [ReportAgent]
  ↓
{ reply, steps, agent_results }
```

---

## Agent Flow Diagrams

### Component Map

```
T6  intent_classifier.py       intent → 9 types
T27 registry.py                AgentRegistry  (7 registered)
T23 orchestrator.py            AgentOrchestrator (/analyze pipeline)
T31 chat_orchestrator.py       ChatOrchestrator (/chat pipeline)
T24 planner_agent.py           PlannerAgent → AnalysisPlan
T26 recovery.py                safe_execute()  (retry + timeout)
T28 metrics.py                 MetricsRegistry
T30 workflow_trace.py          TraceStore
T32 parallel_executor.py       ParallelExecutionManager
T33 plugin_loader.py           PluginLoader (auto-discovery)
T35 evaluator.py               AgentEvaluator
T40 ─ playground page
T41 ─ dashboard/agents page

agents/
├── base_agent.py              (ABC: execute, add_step)
├── data_master_agent.py       Master orchestrator
├── data_agent.py              pandas + DeepSeek analysis
├── audit_agent.py             data quality: nulls, duplicates, Z-score
├── chart_agent.py             line/bar/pie generation
├── report_agent.py            DeepSeek markdown report
├── style_agent.py             theme detection + application
├── export_agent.py            Excel/Word/PNG export

plugins/                       (T33: auto-discovered)
```

### Agent Execution Model

```
Intent → registry.get_intent_agents() → ParallelExecutionManager
                                           ↓
                                     Group 1: [DataAgent]
                                     Group 2: [AuditAgent ‖ ChartAgent]
                                     Group 3: [ReportAgent]
                                     Group 4: [StyleAgent ‖ ExportAgent]
```

---

## Memory Flow Diagrams

```
memory/
├── memory_manager.py          Central orchestrator (singleton)
├── user_memory.py             Layer 1: preferences (category=preference)
├── workspace_memory.py        Layer 2: session snapshots
├── conversation_memory.py     Layer 3: chat history
├── longterm_memory.py         Layer 4: KPI + trend + anomaly
├── memory_router.py           T25: selective retrieval by plan
├── memory_compressor.py       T37: summarize history
└── compressed_memory.py       T37: ORM model

DB Tables:
  user_memories, workspace_memories, conversation_memories,
  analysis_memories, compressed_memories
```

### Write Path
```
/analyze → mgr.save_workspace() + mgr.save_analysis_memory()
/chat → _persist_chat() → chat_messages
/chat → mgr.save_conversation_message() → conversation_memories
T7 → _persist_preferences() → user_preferences + user_memories
```

### Read Path (RAG)
```
/agent-chat →
  MemoryManager.retrieve_relevant_memories()
    ├── user_preferences
    ├── workspace_history
    ├── recent_conversations
    └── historical_analyses
  → build_memory_prompt() → injected into context
```

---

## RAG Flow Diagram (T34 + T43)

```
User Query
  ↓
RetrieverService.retrieve_for_prompt(query)
  ↓
KnowledgeBase.search(query, top_k=3)
  ↓
Keyword scoring: title(+3), content(+2), keywords(+2)
  ↓
"[Knowledge Context]
 - ROE (Return on Equity): ROE = Net Income / Shareholder Equity...
 - Z-Score Outlier Detection: Z = (X - mean) / std..."
  ↓
Injected into AI prompt: memory_prefix + knowledge_context + base_prompt
```

---

## Main File Index

### Backend Core (Tier 1 — Must Read First)

| File | KB | Purpose | Difficulty |
|------|-----|---------|------------|
| `main.py` | 54 | FastAPI app, 55 routes, auth, session | 5 |
| `database.py` | 2.4 | SQLAlchemy engine, WAL, FK pragma | 2 |
| `config.py` | 3.4 | Centralized configuration | 1 |
| `auth_service.py` | 2.9 | JWT + bcrypt authentication | 2 |
| `middleware.py` | 4.1 | Rate limiter + body size guard | 3 |

### Agent System (Tier 2)

| File | KB | Purpose | Difficulty |
|------|-----|---------|------------|
| `agents/base_agent.py` | 0.6 | Abstract BaseAgent | 1 |
| `agents/registry.py` | 2.7 | Dynamic AgentRegistry | 2 |
| `agents/orchestrator.py` | 15.1 | /analyze pipeline orchestrator | 5 |
| `agents/data_master_agent.py` | 4.2 | Master orchestrator | 4 |
| `agents/chat_orchestrator.py` | 8.4 | /chat pipeline orchestrator | 4 |
| `agents/planner_agent.py` | 5.1 | AnalysisPlan + PlannerAgent | 3 |
| `agents/parallel_executor.py` | 4.3 | ParallelExecutionManager | 4 |
| `agents/recovery.py` | 4.0 | safe_execute, retry, timeout | 3 |
| `agents/evaluator.py` | 4.0 | AgentEvaluator | 2 |
| `agents/metrics.py` | 2.7 | MetricsRegistry | 2 |
| `agents/plugin_loader.py` | 2.7 | PluginLoader (auto-discovery) | 2 |
| `agents/chat_planner_agent.py` | 1.7 | ChatPlannerAgent | 2 |
| `agents/data_agent.py` | 4.9 | pandas + DeepSeek analysis | 4 |
| `agents/audit_agent.py` | 4.9 | Data quality audit | 3 |
| `agents/chart_agent.py` | 2.3 | Chart generation | 3 |
| `agents/report_agent.py` | 3.7 | Report generation | 3 |
| `agents/style_agent.py` | 2.3 | Theme/style | 2 |
| `agents/export_agent.py` | 3.4 | File export | 3 |

### Memory System (Tier 3)

| File | KB | Purpose | Difficulty |
|------|-----|---------|------------|
| `memory/memory_manager.py` | 10.8 | Central memory orchestrator | 4 |
| `memory/memory_router.py` | 5.2 | Selective retrieval by plan | 3 |
| `memory/memory_compressor.py` | 3.7 | Memory summarization | 3 |
| `memory/user_memory.py` | 4.9 | User preferences CRUD | 2 |
| `memory/workspace_memory.py` | 6.3 | Workspace snapshots | 3 |
| `memory/conversation_memory.py` | 4.1 | Conversation history | 2 |
| `memory/longterm_memory.py` | 6.1 | Analysis history | 3 |

### LLM / Knowledge / Tools (Tier 4)

| File | KB | Purpose | Difficulty |
|------|-----|---------|------------|
| `llm/base_provider.py` | 0.4 | Abstract provider interface | 1 |
| `llm/deepseek_provider.py` | 2.6 | DeepSeek API wrapper | 3 |
| `llm/provider_registry.py` | 0.9 | Provider registry | 1 |
| `llm/model_router.py` | 2.3 | Task→provider routing | 2 |
| `knowledge/knowledge_base.py` | 2.7 | JSON knowledge store | 2 |
| `knowledge/retriever.py` | 2.3 | RAG retrieval + formatting | 3 |
| `tools/base_tool.py` | 0.5 | BaseTool ABC | 1 |
| `tools/registry.py` | 1.1 | ToolRegistry | 1 |
| `tools/excel_tool.py` | 0.8 | Excel parsing | 2 |
| `tools/chart_tool.py` | 2.2 | Chart generation | 2 |
| `prompt/prompt_manager.py` | 1.9 | Template manager | 1 |

### Infrastructure (Tier 5)

| File | KB | Purpose | Difficulty |
|------|-----|---------|------------|
| `session_store.py` | 10.3 | Session persistence (parquet+DB) | 4 |
| `workflow_engine.py` | 7.8 | Multi-agent pipeline engine | 4 |
| `workflow_trace.py` | 3.7 | Execution trace + visualization | 3 |
| `workflow_definition.py` | 3.4 | Reusable workflow templates | 2 |
| `approval_store.py` | 3.0 | Human-in-the-loop approval | 2 |
| `cost_tracker.py` | 3.3 | LLM cost tracking | 2 |
| `intent_classifier.py` | 4.5 | Unified intent classifier | 3 |
| `export_service.py` | 18.5 | Excel/Word/PNG export logic | 4 |
| `theme_service.py` | 11.0 | Style/theme system | 3 |

### Frontend (Tier 6)

| File | KB | Purpose | Difficulty |
|------|-----|---------|------------|
| `app/page.tsx` | 27.6 | Workspace (main page) | 5 |
| `app/analytics/page.tsx` | 8.8 | Home/Overview dashboard | 3 |
| `app/reports/page.tsx` | 10.6 | History center | 3 |
| `app/memory/page.tsx` | 13.6 | AI memory management | 3 |
| `app/playground/page.tsx` | 4.2 | Agent playground | 2 |
| `app/dashboard/agents/page.tsx` | 6.9 | Agent operations dashboard | 3 |
| `components/NavBar.tsx` | 2.6 | Navigation bar | 2 |
| `components/ErrorBoundary.tsx` | 1.0 | React error boundary | 1 |
| `lib/WorkspaceContext.tsx` | 6.9 | Global state + localStorage | 4 |
| `lib/AuthContext.tsx` | 2.0 | Auth state | 2 |
| `lib/api.ts` | 1.0 | API fetch wrapper | 1 |
| `lib/config.ts` | 0.1 | API_BASE config | 1 |

---

## Recommended Learning Order

### Phase 1 — Core Infrastructure (2 hours)
```
1. config.py              ← centralized settings
2. database.py            ← engine, session, WAL, FK
3. auth_service.py        ← JWT + bcrypt
4. middleware.py          ← rate limit + body size
5. user_model.py          ← first ORM model
6. main.py (first 200 lines) ← app setup, imports
```

### Phase 2 — Agent Foundation (3 hours)
```
1. agents/base_agent.py         ← ABC
2. agents/registry.py           ← dynamic registration
3. intent_classifier.py         ← 9-intent classification
4. agents/planner_agent.py      ← AnalysisPlan
5. agents/orchestrator.py       ← /analyze pipeline
6. agents/data_master_agent.py  ← Master orchestrator
7. agents/chat_orchestrator.py  ← /chat pipeline
```

### Phase 3 — Agent Sub-System (2 hours)
```
1. agents/data_agent.py         ← analysis
2. agents/audit_agent.py        ← quality
3. agents/chart_agent.py        ← charts
4. agents/recovery.py           ← fault tolerance
5. agents/metrics.py            ← observability
6. agents/evaluator.py          ← quality scores
7. agents/parallel_executor.py  ← concurrent exec
```

### Phase 4 — Memory System (2 hours)
```
1. memory/memory_manager.py     ← central orchestrator
2. memory/user_memory.py        ← Layer 1
3. memory/workspace_memory.py   ← Layer 2
4. memory/conversation_memory.py← Layer 3
5. memory/longterm_memory.py    ← Layer 4
6. memory/memory_router.py      ← selective retrieval
7. memory/memory_compressor.py  ← summarization
```

### Phase 5 — Knowledge & Tools (1 hour)
```
1. llm/base_provider.py         ← abstract interface
2. llm/deepseek_provider.py     ← DeepSeek wrapper
3. llm/provider_registry.py     ← multi-provider registry
4. knowledge/knowledge_base.py  ← static knowledge
5. knowledge/retriever.py       ← RAG retrieval
6. tools/registry.py            ← tool registry
7. prompt/prompt_manager.py     ← template manager
```

### Phase 6 — Infrastructure (2 hours)
```
1. session_store.py             ← session persistence
2. workflow_engine.py           ← pipeline engine
3. workflow_trace.py            ← execution tracing
4. cost_tracker.py              ← cost tracking
5. approval_store.py            ← human-in-loop
6. export_service.py            ← file export
7. theme_service.py             ← style system
```

---

## Call Chain Reference

### Analyze Request
```
main.py:analyze_excel()
  → _validate_excel_upload()
  → memory_router.route()              [T25]
  → orchestrator.run_analysis_pipeline() [T23]
      → pd.read_excel()
      → _convert_excel_dates()
      → planner.plan()                 [T24]
      → retriever.retrieve_for_prompt() [T43]
      → _generate_charts()
      → _ai_analyze()                  [DeepSeek]
      → _persist_dashboard()
      → _persist_memory()
      → session_store.save()           [T1]
      → trace_store.save()             [T30]
```

### Chat Request
```
main.py:chat()
  → _get_session()                     [T1]
  → classify_for_chat()                [T6]
  → ChatOrchestrator.execute()         [T31]
      → DeepSeek API (tool-calling)
      → trace_store.save()             [T30]
      → metrics_registry.record()      [T28]
```

### Agent Chat Request
```
main.py:agent_chat()
  → MemoryManager.retrieve_relevant_memories()
  → WorkflowEngine.run()
      → DataMasterAgent.execute()
          → classify()                 [T6]
          → registry.get_intent_agents() [T27]
          → ParallelExecutionManager.execute() [T32]
              → safe_execute()          [T26]
          → evaluator.evaluate()        [T35]
          → cost_tracker.record()       [T44]
```

---

## Technology Stack Summary

```
Backend (Python 3.11):
  Framework:   FastAPI 0.136 + Uvicorn 0.48
  ORM:         SQLAlchemy 2.0 + SQLite (WAL mode)
  Auth:        python-jose JWT + passlib bcrypt
  Data:        pandas 3.0 + openpyxl + pyarrow (parquet)
  LLM:         DeepSeek API (deepseek-chat)
  Rate Limit:  slowapi + limits
  Export:      python-docx + matplotlib
  Config:      pydantic + dotenv

Frontend (Node 22):
  Framework:   Next.js 16 (App Router) + React 19
  Language:    TypeScript 5
  Styling:     Tailwind CSS 4 (dark mode)
  Charts:      Recharts 3.8
  State:       React Context + localStorage
```
