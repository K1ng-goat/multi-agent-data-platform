# T43 RAG Retrieval

> **Date**: 2026-06-04  
> **Endpoint**: `GET /knowledge/stats`

---

## Architecture

```
Agent (DataAgent, AuditAgent, ReportAgent)
  ↓
retriever.retrieve_for_prompt(query)
  ↓
KnowledgeBase.search(query, top_k=3)
  ↓
"[Knowledge Context]\n- ROE: ...\n- Z-Score: ..."
  ↓
Injected into AI analysis prompt (memory + knowledge + base_prompt)
```

## Retrieval Flow

```
search("roe")           → 1 result: ROE (Return on Equity)
search("missing values") → 1 result: Missing Value Treatment
retrieve_for_prompt()   → "[Knowledge Context]\n- ..."
```

## Metrics

```
GET /knowledge/stats →
  retrieval_count: 3
  hit_count: 3
  hit_rate: 100.0%
  top_categories: [(finance, 2), (data_quality, 1)]
```

## Files

| File | Change |
|------|--------|
| `knowledge/retriever.py` | **NEW** — RetrieverService (75 lines) |
| `agents/orchestrator.py` | **MODIFIED** — knowledge injected into prompt |
| `main.py` | **MODIFIED** — +GET /knowledge/stats |
| `docs/T43_RAG_RETRIEVAL.md` | Design document |

## Verification

```
search("roe"):         1 result (ROE)
search("missing"):     1 result (Missing Values)
retrieve_for_prompt:   147 chars
stats:                 hit_rate=100%
Routes:                53
```