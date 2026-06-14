"""ExcelTool — Excel file parsing and validation."""
from __future__ import annotations
import io
import pandas as pd
from .base_tool import BaseTool
from .registry import tool_registry


class ExcelTool(BaseTool):
    name = "ExcelTool"
    description = "Parse and validate Excel files"

    def execute(self, **kwargs) -> dict:
        file_bytes = kwargs.get("file_bytes")
        if file_bytes is None:
            return {"ok": False, "error": "file_bytes required"}

        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        return {
            "ok": True,
            "dataframe": df,
            "shape": {"rows": df.shape[0], "columns": df.shape[1]},
            "columns": df.columns.tolist(),
        }


tool_registry.register(ExcelTool())
