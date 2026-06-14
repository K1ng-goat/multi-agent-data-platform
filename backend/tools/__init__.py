"""Dynamic Tool Registry — plugin-style tool discovery and execution."""
from .base_tool import BaseTool
from .registry import ToolRegistry, tool_registry

# Import tools to trigger registration
from .excel_tool import ExcelTool       # noqa: F401
from .chart_tool import ChartTool       # noqa: F401
from .export_tool import ExportTool     # noqa: F401
from .memory_tool import MemoryTool     # noqa: F401
from .theme_tool import ThemeTool       # noqa: F401
