# T29 Tool Registry

> **Date**: 2026-06-04  
> **Baseline**: T28 Agent Metrics  
> **Endpoint**: `GET /tools`

---

## Architecture

```
Agents
  ↓
ToolRegistry.get("ChartTool")
  ↓
ChartTool.execute(dataframe=df)
  ↓
Result {ok: true, charts: [...]}
```

## Registered Tools (5)

```
ExcelTool     — Parse and validate Excel files
ChartTool     — Generate line, bar, and pie chart configurations
ExportTool    — Export data to Excel, Word, and chart images
MemoryTool    — Save and retrieve analysis memories
ThemeTool     — Apply and list document style themes
```

## Registration Flow

```
Module import (tools/__init__.py)
  ↓
import excel_tool  → ExcelTool()
  → tool_registry.register(ExcelTool())
  ↓
ToolRegistry._tools["ExcelTool"] = instance
```

## API

### GET /tools

```json
{
  "tools": [
    {"name": "ExcelTool",   "description": "Parse and validate Excel files"},
    {"name": "ChartTool",   "description": "Generate line, bar, and pie chart configurations"},
    {"name": "ExportTool",  "description": "Export data to Excel, Word, and chart images"},
    {"name": "MemoryTool",  "description": "Save and retrieve analysis memories"},
    {"name": "ThemeTool",   "description": "Apply and list document style themes"}
  ]
}
```

## Tool Usage Pattern

```python
from tools import tool_registry

# Parse Excel
result = tool_registry.get("ExcelTool").execute(file_bytes=data)

# Generate charts
result = tool_registry.get("ChartTool").execute(dataframe=df)

# List themes
result = tool_registry.get("ThemeTool").execute(action="list")
```

## Files

| File | Change |
|------|--------|
| `tools/__init__.py` | **NEW** — package init, triggers registration |
| `tools/base_tool.py` | **NEW** — BaseTool ABC (15 lines) |
| `tools/registry.py` | **NEW** — ToolRegistry singleton (35 lines) |
| `tools/excel_tool.py` | **NEW** — Excel parsing |
| `tools/chart_tool.py` | **NEW** — Chart generation |
| `tools/export_tool.py` | **NEW** — File export |
| `tools/memory_tool.py` | **NEW** — Memory persistence |
| `tools/theme_tool.py` | **NEW** — Theme/style |
| `main.py` | **MODIFIED** — +GET /tools endpoint |
| `docs/T29_TOOL_REGISTRY.md` | Design document |

## Verification

```
list_tools():         5 tools registered
ExcelTool:            parse OK
ChartTool:            1 chart generated
ThemeTool:            4 themes listed
MemoryTool:           get_preferences OK
ExportTool:           validation OK
GET /tools:           200
Routes:               33 (30 + 2 metrics + 1 tools)
/analyze:             200 unchanged
```
