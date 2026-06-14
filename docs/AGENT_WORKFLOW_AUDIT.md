# T22 Agent Workflow Audit

> **Date**: 2026-06-04  
> **Version**: v1.0 baseline  
> **Method**: Read-only code analysis

---

## 1. Agent Inventory (8 agents, 642 lines)

| # | Agent | File | Lines | Role | External Deps |
|---|-------|------|-------|------|---------------|
| 0 | `BaseAgent` | `base_agent.py` | 18 | Abstract base: `execute()`, `add_step()` | — |
| 1 | **`DataMasterAgent`** | `data_master_agent.py` | 96 | Orchestrator: intent→routing→pipeline | `intent_classifier` |
| 2 | `DataAgent` | `data_agent.py` | 114 | Statistical summary, DeepSeek AI analysis | `pandas`, `httpx` (DeepSeek) |
| 3 | `ChartAgent` | `chart_agent.py` | 60 | Line/Bar/Pie chart generation | `pandas`, `main._generate_charts` |
| 4 | `AuditAgent` | `audit_agent.py` | 126 | Data quality: nulls, duplicates, Z-score | `pandas` |
| 5 | `ReportAgent` | `report_agent.py` | 93 | Markdown report via DeepSeek | `httpx` (DeepSeek) |
| 6 | `StyleAgent` | `style_agent.py` | 59 | Theme detection, style application | `theme_service` |
| 7 | `ExportAgent` | `export_agent.py` | 76 | Excel/Word/Chart file export | `export_service` |

---

## 2. Current Workflow (3 Parallel Paths)

### Path A — /chat (Tool-Calling Single Agent)

```
User message
  ↓
/chat endpoint
  ↓
_classify_intent(msg)  →  "workflow" | "chat"
  ↓
  ├─ "chat"  →  DeepSeek function-calling (6 tools, max 3 rounds)
  │              compute_stat, sort_data, group_by,
  │              analyze_trend, filter_data, describe_data
  │              ↓
  │            Reply
  │
  └─ "workflow" → workflow.py plan_workflow()
                    ↓
                   _execute_tool() x N steps
                    ↓
                   workflow.py generate_report()
                    ↓
                   Reply + report + timeline
```

**Limitation**: No agent pipeline. Tools are hard-coded function implementations, not agent classes.

### Path B — /agent-chat (Multi-Agent Pipeline)

```
User message
  ↓
/agent-chat endpoint
  ↓
MemoryManager.retrieve_relevant_memories()
  ↓
WorkflowEngine.run()
  ↓
DataMasterAgent.execute()
  ├── classify(user_message)  →  1 of 9 intents
  ├── plan_tasks(intent)       →  agent routing list
  └── execute_pipeline(tasks)  →  sequential agent execution
       ├── DataAgent.execute()
       ├── AuditAgent.execute()
       ├── ChartAgent.execute()
       ├── ReportAgent.execute()
       ├── StyleAgent.execute()
       └── ExportAgent.execute()
  ↓
format_response()  → {reply, steps, charts, exports}
```

**Limitation**: Strictly sequential. Agents cannot run in parallel even when independent.

### Path C — /analyze (Monolithic)

```
Upload Excel
  ↓
pandas.read_excel()
  ↓
_convert_excel_dates()
  ↓
_generate_charts()     ← monolithic chart function (not ChartAgent)
  ↓
DeepSeek API call       ← inline prompt (not DataAgent)
  ↓
ds.update_snapshot()    ← dashboard service
  ↓
MemoryManager.save_*()  ← memory persistence
  ↓
Return {session_id, charts, analysis}
```

**Limitation**: Bypasses the entire agent system. All logic is inline in main.py (200+ lines).

---

## 3. Intent Routing Map

```
INTENT_AGENT_MAP:
  analyze            → [DataAgent]
  chart              → [ChartAgent]
  audit              → [AuditAgent]
  report             → [ReportAgent]
  style              → [StyleAgent]
  export             → [ExportAgent]
  full_report        → [Data, Audit, Chart, Report, Style, Export]  (all 6)
  data_with_charts   → [Data, Chart]
  analyze_and_report → [Data, Report]
```

---

## 4. Identified Limitations

### Architectural

| # | Limitation | Impact |
|---|-----------|--------|
| L1 | `/analyze` bypasses agents entirely | Inline logic, no step visualization, no parallelism |
| L2 | Agents execute strictly sequentially | ChartAgent waits for AuditAgent even when independent |
| L3 | `/chat` has no agent at all | 6 hard-coded tool functions, no agent architecture |
| L4 | No agent lifecycle hooks | Cannot do pre/post-processing, retry, timeout |
| L5 | Shared context dict is mutation-heavy | Any agent can modify any key, no data contract |

### Observability

| # | Limitation | Impact |
|---|-----------|--------|
| L6 | Agent steps use print() | No structured logging, no metrics, no tracing |
| L7 | No per-agent timing | Cannot identify slow agents |
| L8 | No error recovery | Agent failure stops entire pipeline |

### Extensibility

| # | Limitation | Impact |
|---|-----------|--------|
| L9 | Adding new agent requires routing map update + keyword list update | High coupling |
| L10 | Agent registration is manual dict | No discovery/plugin mechanism |
| L11 | No agent configuration | All agents use same DeepSeek parameters |

### Performance

| # | Limitation | Impact |
|---|-----------|--------|
| L12 | Sequential execution only | Full pipeline = sum of all agent times |
| L13 | No caching between agent calls | ReportAgent re-calls DeepSeek with same data as DataAgent |
| L14 | No streaming responses | User waits for entire pipeline to complete |

---

## 5. Current Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FASTAPI ENDPOINTS                        │
│  /analyze          /chat               /agent-chat              │
│  (monolithic)      (tool-calling)      (agent pipeline)         │
│       │                 │                     │                  │
│       │                 │                     ▼                  │
│       │                 │          ┌──────────────────┐         │
│       │                 │          │  WorkflowEngine   │         │
│       │                 │          │  DataMasterAgent  │         │
│       │                 │          └────────┬─────────┘         │
│       │                 │                   │                    │
│       │                 │     ┌─────────────┼─────────────┐     │
│       │                 │     │             │             │     │
│       │                 │     ▼             ▼             ▼     │
│       │                 │  DataAgent    AuditAgent   ChartAgent │
│       │                 │  ReportAgent  StyleAgent  ExportAgent │
│       │                 │     │             │             │     │
│       │                 │     └─────────────┼─────────────┘     │
│       │                 │                   │                    │
│       ▼                 ▼                   ▼                    │
│  ┌────────┐      ┌──────────┐      ┌──────────────┐            │
│  │ pandas │      │ DeepSeek │      │ export_      │            │
│  │ inline │      │ function │      │ service      │            │
│  │ charts │      │ calling  │      │ theme_service│            │
│  └────────┘      └──────────┘      └──────────────┘            │
│       │                 │                   │                    │
│       └─────────────────┼───────────────────┘                    │
│                         ▼                                         │
│              ┌──────────────────┐                                │
│              │  Memory + Session│                                │
│              │  Persistence     │                                │
│              └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Agent Upgrade Opportunities

### Phase A — Unify Entry Points

```
Goal: Route /analyze and /chat through the agent pipeline
Impact: 200+ lines removed from main.py, consistent step visualization
```

### Phase B — Parallel Execution

```
Goal: Run independent agents concurrently
Impact: full_report pipeline time reduced from sum-of-all to max(agent times)
```

### Phase C — Agent Config & Discovery

```
Goal: Plugin-style agent registration, per-agent DeepSeek parameters
Impact: New agents added without touching routing code
```

### Phase D — Streaming & Observability

```
Goal: SSE streaming, per-agent timing metrics, structured logging
Impact: Real-time progress in frontend, performance dashboards
```

---

## 7. Summary

```
Total agents:        8 (1 base + 1 master + 6 sub)
Agent code:          642 lines (8% of backend ~4200 lines)
Endpoints using agents: 1/3 (/agent-chat only)
Endpoints bypassing:    2/3 (/analyze, /chat)
Execution model:        Sequential only
Observability:          print() + context["steps"]
Extensibility:          Manual routing map
```
