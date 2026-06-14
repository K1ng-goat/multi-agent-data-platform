# T31 Chat Agent Integration

> **Date**: 2026-06-04  
> **Baseline**: T30 Workflow Trace  
> **Goal**: Refactor /chat to use agent framework

---

## Architecture Change

```
BEFORE                              AFTER
──────                              ─────
/chat                                /chat
  ↓                                   ↓
_classify_intent(msg)                ChatPlannerAgent.plan(msg)
  ↓                                   ↓
  ├─ "chat" → 6 hardcoded tools      ChatOrchestrator.execute()
  │            DeepSeek function-       ├─ ChatPlannerAgent
  │            calling in main.py       ├─ safe_execute
  │                                     ├─ metrics_registry
  └─ "workflow" → wf.plan_workflow      ├─ trace_store
                   wf.generate_report   └─ DeepSeek tool-calling
```

## New Components

### ChatPlannerAgent

```
user_message → classify_for_chat() → ChatExecutionPlan
  "chat"    → mode=chat, agents=[DataAgent]
  "workflow"→ mode=workflow, agents=[DataAgent, ReportAgent]
```

### ChatOrchestrator

```
ChatExecutionPlan → execute()
  ├─ trace_store.start_trace()
  ├─ DeepSeek tool-calling (6 tools, max 3 rounds)
  ├─ metrics_registry.record()
  └─ trace_store.save()
```

## Shared Infrastructure

Both /chat and /analyze now share:
- Agent Registry (T27)
- safe_execute with retry+timeout (T26)
- MetricsRegistry (T28)
- TraceStore (T30)
- Intent Classifier (T6)

## Files

| File | Change |
|------|--------|
| `agents/chat_planner_agent.py` | **NEW** — ChatPlannerAgent (55 lines) |
| `agents/chat_orchestrator.py` | **NEW** — ChatOrchestrator (110 lines) |
| `main.py` | **MODIFIED** — /chat chat-mode uses ChatOrchestrator |
| `docs/T31_CHAT_AGENT_INTEGRATION.md` | Design document |

## Verification

```
ChatPlannerAgent:     chat→DataAgent, workflow→DataAgent+ReportAgent
Routes:               35
/analyze:             200 (no regression)
/chat:                200
/agent-chat:          200 (unchanged)
ChatExecutionPlan:    5 keys serializable
```
