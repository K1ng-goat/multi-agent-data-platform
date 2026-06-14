# T34 Agent Knowledge Base (RAG Foundation)

> **Date**: 2026-06-04  
> **Endpoints**: `GET /knowledge/categories`, `GET /knowledge/search`

---

## Architecture

```
knowledge/
├── knowledge_base.py     — in-memory store + keyword search
├── documents/
│   ├── finance.json      — ROE, Revenue Growth, Gross Margin
│   ├── statistics.json   — Z-Score, Correlation, P-Value
│   ├── data_quality.json — Missing Values, Duplicates
│   └── visualization.json— Chart Selection, Color Best Practices
```

## Knowledge Entry Format

```json
{
  "id": "fin_001",
  "category": "finance",
  "title": "ROE (Return on Equity)",
  "content": "ROE = Net Income / Shareholder Equity...",
  "keywords": ["roe", "return on equity", "profitability"]
}
```

## API

### GET /knowledge/categories

```json
{"categories": ["finance", "statistics", "data_quality", "visualization"]}
```

### GET /knowledge/search?q=roe

```json
{"query": "roe", "count": 1, "results": [{"title": "ROE ...", "content": "..."}]}
```

## Scoring

```
q in title   → +3
q in content → +2
kw in q      → +2
q in kw      → +1
```

## Files

| File | Change |
|------|--------|
| `knowledge/__init__.py` | **NEW** |
| `knowledge/knowledge_base.py` | **NEW** — KnowledgeBase class (75 lines) |
| `knowledge/documents/{4 files}` | **NEW** — 10 JSON entries |
| `main.py` | **MODIFIED** — +2 endpoints |
| `docs/T34_KNOWLEDGE_BASE.md` | Design document |

## Verification

```
Entries:          10 (4 categories)
search("roe"):    1 result, ROE
search("chart"):  1 result, Chart Selection
search("xyz"):    0 results
Categories:       200
Search:           200
Routes:           38
/analyze:         200
```
