# Project Learning Path

> **Target**: Teach the project to its author  
> **Duration**: ~20 hours across 5 levels  
> **Prerequisites**: Python, FastAPI basics, React basics, SQLAlchemy basics

---

## Level 1 — Can Explain Architecture

**Goal**: Understand what this project is, how it's organized, and how data flows.

### Concepts

| # | Concept | What to Learn |
|---|---------|---------------|
| 1.1 | Project Purpose | AI-powered Excel data analysis with multi-agent orchestration |
| 1.2 | Monorepo Structure | `backend/` (FastAPI) + `frontend/` (Next.js) + Docker |
| 1.3 | Request Lifecycle | Browser → FastAPI route → orchestrator → agents → response |
| 1.4 | Database Schema | 11 SQLite tables: users, sessions, memory ×4, reports, chat, preferences |
| 1.5 | Auth Flow | JWT HS256, 7-day expiry, bcrypt passwords, Bearer token |
| 1.6 | Session Model | L1 (in-memory dict) + L2 (SessionStore: parquet + SQLite) |

### Files to Read

```
backend/config.py             ← all settings in one place
backend/database.py           ← SQLAlchemy engine + WAL setup
backend/user_model.py         ← first ORM model (simplest)
backend/auth_service.py       ← JWT token creation + validation
backend/main.py               ← first 200 lines: app setup, imports, middleware
frontend/src/app/page.tsx     ← Workspace: how the frontend starts
frontend/src/app/layout.tsx   ← root layout structure
frontend/src/lib/config.ts    ← API_BASE config
```

### Prerequisites

- Python 3.11 virtual environment running
- `pip install -r backend/requirements.txt`
- `npm install` in frontend/
- `set DEEPSEEK_API_KEY=sk-xxx` (or skip — basic routes work without it)

### Exercises

1. **Start the project locally**
   ```bash
   cd backend && python main.py
   cd frontend && npm run dev
   ```
   Visit http://localhost:3000. Register a user. Observe the navbar (Home, Workspace, Reports, Memory).

2. **Trace a request**
   Open `main.py`. Find the `GET /` endpoint. Follow the code path:
   ```
   @app.get("/") → root() → return {"message": "..."}
   ```
   Then trace `GET /themes`:
   ```
   @app.get("/themes") → list_themes() → ts.THEMES → return JSON
   ```

3. **Draw the architecture**
   On paper, draw:
   ```
   Browser → FastAPI → SQLite
                    → DeepSeek API (optional)
   ```
   Label the 55 route endpoints. Group them by category (auth, core, memory, export, etc.).

4. **Explain the database**
   Open `database.py` and `init_db()`. List all 11 tables. For each, write one sentence about what it stores.

5. **Run the health check**
   ```bash
   curl http://localhost:8000/
   curl http://localhost:8000/themes
   ```
   Verify both return 200. Note the Chinese theme names in `/themes` — proof that UTF-8 encoding works.

---

## Level 2 — Can Modify APIs

**Goal**: Understand the route layer, add a new endpoint, modify request/response schemas.

### Concepts

| # | Concept | What to Learn |
|---|---------|---------------|
| 2.1 | FastAPI Route Patterns | `@app.get`, `@app.post`, Pydantic `BaseModel`, `Depends` |
| 2.2 | JWT Auth Dependency | `user: User = Depends(get_current_user)` — how it works |
| 2.3 | Rate Limiting | `@limiter.limit("10/minute")` + slowapi middleware |
| 2.4 | File Upload Validation | `_validate_excel_upload()` — extension, MIME, 50MB |
| 2.5 | Response Patterns | `return {"key": value}` → JSONResponse → frontend |
| 2.6 | Session Lookup | `_get_session(session_id, user_id)` — L1+L2 fallback |

### Files to Read

```
backend/main.py               ← full file (55 routes, study the patterns)
backend/middleware.py          ← MaxBodySizeMiddleware + rate limiter
backend/main.py:L57-77         ← _get_session() fallback logic
backend/main.py:L63-90         ← _validate_excel_upload()
backend/main.py:L558-575       ← /analyze route (16-line thin controller!)
frontend/src/lib/api.ts        ← apiFetch() wrapper
frontend/src/lib/AuthContext.tsx ← how auth token flows to frontend
```

### Prerequisites

- Level 1 completed
- One API endpoint understood end-to-end

### Exercises

1. **Add a simple GET endpoint**
   In `main.py`, add:
   ```python
   @app.get("/hello")
   async def hello():
       return {"greeting": "Hello from AI Data Platform"}
   ```
   Test: `curl http://localhost:8000/hello`
   Then add auth protection:
   ```python
   @app.get("/hello")
   async def hello(user: User = Depends(get_current_user)):
       return {"greeting": f"Hello {user.username}"}
   ```
   Test without token → 401. Test with token → 200.

2. **Modify an existing endpoint**
   Find `GET /memory/summary`. Add a new field `"timestamp"` to the response.
   Trace the data flow: route → `mgr.get_memory_summary()` → `memory_manager.py`.
   Verify the frontend Memory page still works.

3. **Add a Pydantic request model**
   Create a new model:
   ```python
   class FeedbackRequest(BaseModel):
       session_id: str
       rating: int
       comment: str = ""
   ```
   Add a `POST /feedback` endpoint that validates the input and returns it.
   Test with valid JSON → 200. Test with missing field → 422.

4. **Understand rate limiting**
   Find `@limiter.limit("10/minute")` in main.py. Count how many endpoints have it.
   Explain why `/chat`, `/agent-chat`, `/analyze` are rate-limited but `/themes` is not.

5. **Trace the session lifecycle**
   Start at `POST /analyze`. Follow `session_id` creation → `sessions[sid] = {...}` → `session_store.save()` → `_get_session()` on next request.
   Draw the L1 (dict) + L2 (parquet+DB) flow on paper.

---

## Level 3 — Can Add Agents

**Goal**: Understand the agent system, register a new agent, write a plugin.

### Concepts

| # | Concept | What to Learn |
|---|---------|---------------|
| 3.1 | BaseAgent Contract | `execute(context) → context`, `add_step()` |
| 3.2 | AgentRegistry | `register()`, `get()`, `list_agents()`, `get_intent_agents()` |
| 3.3 | Intent Classifier | Keyword-based → 9 intent types → agent routing |
| 3.4 | Planning | `AnalysisPlan` with boolean flags + `required_agents` |
| 3.5 | Fault Tolerance | `safe_execute()` — retry, timeout, graceful degradation |
| 3.6 | Plugin System | Auto-discovery via `PluginLoader`, drop-in `plugins/` directory |
| 3.7 | Metrics + Evaluation | `metrics_registry.record()`, `evaluator.evaluate()` |

### Files to Read

```
agents/base_agent.py           ← the contract every agent follows
agents/registry.py             ← how agents are registered + discovered
agents/data_agent.py           ← study a real agent: analysis
agents/audit_agent.py          ← study a real agent: audit (simpler)
agents/recovery.py             ← safe_execute: retry + timeout
agents/metrics.py              ← how metrics are collected
agents/evaluator.py            ← quality scoring heuristics
agents/plugin_loader.py        ← auto-discovery mechanism
agents/plugins/__init__.py     ← where new plugins go
intent_classifier.py           ← keyword matching logic
```

### Prerequisites

- Level 2 completed
- One existing agent read and understood

### Exercises

1. **Read and trace an agent**
   Open `agents/audit_agent.py`. Trace the `execute()` method:
   ```
   execute(context) → df from context → check nulls → check duplicates → Z-score → quality score → context
   ```
   Draw the input/output on paper. What does it read from context? What does it write?

2. **Create a new agent**
   Create `agents/plugins/summary_agent.py`:
   ```python
   from agents.base_agent import BaseAgent
   from agents.registry import registry

   class SummaryAgent(BaseAgent):
       name = "SummaryAgent"
       description = "Generates a quick data summary"

       async def execute(self, context):
           df = context.get("df")
           if df is not None:
               context["quick_summary"] = f"{df.shape[0]} rows, {df.shape[1]} columns"
           self.add_step(context, "done", "Summary generated")
           return context

   registry.register("SummaryAgent", SummaryAgent)
   ```
   Verify: restart backend. Check `GET /agents` includes SummaryAgent.
   Test via `POST /agent/run {"agent":"SummaryAgent","prompt":"test"}`.

3. **Add a new intent**
   In `intent_classifier.py`, add a new keyword list:
   ```python
   SUMMARY_KEYWORDS = ["summary", "summarize", "overview"]
   ```
   Add logic to `classify()` to detect "summary" intent.
   In `agents/registry.py`, add mapping:
   ```python
   "summary": ["SummaryAgent"]
   ```
   Test: send "give me a summary" to `/chat`. Does it route correctly?

4. **Test fault tolerance**
   Create a deliberately broken agent:
   ```python
   class BrokenAgent(BaseAgent):
       name = "BrokenAgent"
       async def execute(self, context):
           raise RuntimeError("I always fail")
   ```
   Register it. Call via `POST /agent/run`. Verify:
   - Result contains `success: false`
   - Error is logged
   - Other agents still work

5. **Check metrics**
   After running several agent calls:
   ```bash
   curl http://localhost:8000/agent/metrics
   curl http://localhost:8000/agent/evaluation
   ```
   Verify your new agent appears in both.

---

## Level 4 — Can Add Workflows

**Goal**: Understand the full pipeline, create workflow templates, orchestrate multi-agent sequences.

### Concepts

| # | Concept | What to Learn |
|---|---------|---------------|
| 4.1 | Workflow Pipeline | Planner → Router → Orchestrator → Registry → Agents |
| 4.2 | Parallel Execution | `ParallelExecutionManager` — group-based concurrency |
| 4.3 | Workflow Templates | `WorkflowDefinition` — reusable agent sequences |
| 4.4 | Memory Integration | `MemoryRouter` — selective retrieval by plan |
| 4.5 | RAG Integration | `Retriever` — knowledge injection into prompts |
| 4.6 | Human-in-Loop | `ApprovalStore` — pause → approve/reject → continue |
| 4.7 | Workflow Tracing | `TraceStore` — step-by-step execution recording |

### Files to Read

```
workflow_engine.py             ← WorkflowEngine: context creation + response formatting
workflow_definition.py         ← 5 predefined workflow templates
agents/orchestrator.py         ← /analyze pipeline: parse → chart → AI → persist → trace
agents/data_master_agent.py    ← Master orchestrator: intent → plan → execute
agents/parallel_executor.py    ← PARALLEL_GROUPS: dependency-aware execution
agents/chat_orchestrator.py    ← /chat pipeline: tool-calling via DeepSeek
memory/memory_router.py        ← selective retrieval: which layers to query
memory/memory_compressor.py    ← summarization of historical data
approval_store.py              ← pause workflow, await human decision
workflow_trace.py              ← execution trace: WorkflowStep + TraceStore
```

### Prerequisites

- Level 3 completed
- Created at least one agent

### Exercises

1. **Add a new workflow template**
   In `workflow_definition.py`, add:
   ```python
   "data_review": WorkflowDefinition(
       name="data_review",
       description="Quick data review: audit + summary",
       agents=["DataAgent", "AuditAgent"],
       tools=["ExcelTool"],
       category="review",
   )
   ```
   Verify: `curl http://localhost:8000/workflow/templates` shows it.

2. **Modify the parallel execution groups**
   In `agents/parallel_executor.py`, add a new parallel group:
   ```python
   "data_review": [
       ["DataAgent", "AuditAgent"],  # run concurrently
   ],
   ```
   Explain why DataAgent and AuditAgent can run in parallel (both read df, neither writes to the other's output keys).

3. **Trace a full workflow execution**
   Start `POST /analyze` with an Excel file. Follow every log line:
   ```
   [Orchestrator] Excel loaded
   [Orchestrator] charts=3
   [Orchestrator] dashboard/report saved
   [Orchestrator] memory saved
   [SessionStore] parquet written
   [Orchestrator] SessionStore save OK
   [Orchestrator] pipeline complete
   ```
   Map each log to the corresponding function in `orchestrator.py`.

4. **Add an approval checkpoint**
   In a workflow, insert:
   ```python
   from approval_store import approval_store
   approval_store.request(trace.workflow_id, "ReportAgent", "Ready for report?")
   ```
   Check pending: `curl http://localhost:8000/workflow/pending`
   Approve: `curl -X POST http://localhost:8000/workflow/approve/{id}`

5. **Compare sequential vs parallel**
   Create two mock agents that each sleep 200ms. Run them:
   - Sequential: `for agent in [a1, a2]: await agent.execute()`
   - Parallel: `await asyncio.gather(a1.execute(), a2.execute())`
   Measure total time. Confirm parallel is roughly 200ms, sequential is ~400ms.

---

## Level 5 — Can Redesign Architecture

**Goal**: Understand every architectural decision, evaluate tradeoffs, propose redesigns.

### Concepts

| # | Concept | What to Learn |
|---|---------|---------------|
| 5.1 | SQLite vs MySQL | When each makes sense, migration strategy (T16) |
| 5.2 | L1 + L2 Cache Pattern | Why sessions dict was kept (T1 Phase 4 rejected) |
| 5.3 | Sequential vs Parallel | Dependency graph design, context safety in concurrent execution |
| 5.4 | Keyword vs Vector Retrieval | Current keyword RAG, when to upgrade to embeddings |
| 5.5 | Monolithic Route vs Agent Pipeline | Why /analyze was refactored (T23), why /chat was refactored (T31) |
| 5.6 | Fault Tolerance Strategy | Retry counts, timeout values, partial success semantics |
| 5.7 | Multi-LLM Abstraction | Provider pattern, when to add OpenAI/Claude/Gemini |
| 5.8 | Observability Stack | Metrics + Evaluation + Trace + Cost — what each measures |
| 5.9 | Docker Architecture | Backend + Frontend + MySQL, healthchecks, volumes, env vars |

### Files to Read

```
docs/ARCHITECTURE.md           ← v0.1.0 audit (20 technical debts identified)
docs/T23_ORCHESTRATOR_REFACTOR.md ← why /analyze was extracted
docs/T32_PARALLEL_EXECUTION.md ← dependency graph design
docs/T39_MULTI_LLM_FOUNDATION.md ← provider abstraction
docs/T43_RAG_RETRIEVAL.md      ← knowledge injection pipeline
docs/PROJECT_SOURCE_MAP.md     ← full file index with call chains
```

### Prerequisites

- Level 4 completed
- All 55 routes understood
- All 11 database tables understood
- At least one agent and one workflow created

### Exercises

1. **Evaluate a design decision**
   T1 Phase 4 proposed deleting the `sessions` dict. It was **rejected**.
   Read `docs/RELIABILITY_REVIEW.md` and `main.py:_get_session()`.
   Write a one-page analysis: was the right decision made? What would change if this were a multi-server deployment?

2. **Propose a new architecture**
   Current: keyword-based intent classifier (T6) + heuristic planner (T24).
   Alternative: LLM-based intent + planning.
   Write the design: what changes in `intent_classifier.py` and `planner_agent.py`? What are the cost implications (T44)? How would you feature-flag it?

3. **Design a migration plan**
   Current: SQLite production, MySQL code-ready (T16, blocked by Docker Hub).
   Design the migration steps: data export, schema creation, verification, cutover.
   Identify 3 risks and mitigation strategies.

4. **Add a new LLM provider**
   Current: DeepSeek only (T39).
   In `llm/model_router.py`, activate the OpenAI stub:
   ```python
   from llm.openai_provider import OpenAIProvider
   provider_registry.register(OpenAIProvider())
   ```
   Implement `OpenAIProvider` in `llm/openai_provider.py` (use `httpx` to call `https://api.openai.com/v1/chat/completions`).
   Add routing logic: if `OPENAI_API_KEY` is set, route `chat` → `openai`.

5. **Upgrade RAG from keyword to vector**
   Current: `KnowledgeBase.search()` uses keyword matching (T34).
   Design the upgrade: add `sentence-transformers` for embeddings, FAISS for vector search, store vectors alongside knowledge entries.
   What changes in `knowledge/retriever.py`? What's the storage cost? What's the latency impact?

6. **Archive review**
   Read `docs/PRODUCTION_READINESS_REPORT.md` (T20). Note the release score (87/100).
   Identify the 3 remaining blockers. For each, write whether it's been resolved in T21-T44.
   Update the score: what would you give now?

---

## Level Summary

```
Level 1  Architecture     8 files,  5 exercises   2 hours
Level 2  APIs             8 files,  5 exercises   3 hours
Level 3  Agents          11 files,  5 exercises   4 hours
Level 4  Workflows       11 files,  5 exercises   5 hours
Level 5  Architecture     6 files,  6 exercises   6 hours
────────────────────────────────────────────────────────
Total:  44 files studied, 26 exercises, ~20 hours
```

## Quick Reference

```
Pattern                     Where to find it
──────────────────────────────────────────────────────
How to add an endpoint      main.py: any @app.get/@app.post
How to add auth             main.py: user: User = Depends(get_current_user)
How to add rate limiting    main.py: @limiter.limit("10/minute")
How to add an agent         agents/plugins/ ← drop a file
How to add a tool           tools/ ← drop a file
How to add a workflow       workflow_definition.py: WORKFLOW_TEMPLATES
How to add a prompt         prompt/templates/ ← drop a .txt file
How to add knowledge        knowledge/documents/ ← drop a .json file
How to add an LLM provider  llm/ ← implement BaseLLMProvider
How to add a DB table       Create model → import in database.py:init_db()
How to see agent stats      GET /agent/metrics + GET /agent/evaluation
How to see workflow trace   GET /workflow/latest
How to see cost             GET /costs/summary
```
