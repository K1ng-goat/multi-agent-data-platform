"""ChartTool — chart configuration generation."""
from __future__ import annotations
import pandas as pd
from .base_tool import BaseTool
from .registry import tool_registry


class ChartTool(BaseTool):
    name = "ChartTool"
    description = "Generate line, bar, and pie chart configurations"

    def execute(self, **kwargs) -> dict:
        df = kwargs.get("dataframe")
        if df is None:
            return {"ok": False, "error": "dataframe required", "charts": []}

        charts = self._generate(df)
        return {"ok": True, "charts": charts}

    def _generate(self, df: pd.DataFrame) -> list[dict]:
        charts = []
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_cols:
            return charts
        str_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object"]
        label_col = str_cols[0] if str_cols else None
        head = df.head(50)
        labels = head[label_col].astype(str).tolist() if label_col else [str(i + 1) for i in range(len(head))]
        charts.append({
            "type": "line", "title": "Data Trend", "labels": labels,
            "datasets": [{"name": col, "data": head[col].fillna(0).tolist()} for col in numeric_cols[:3]],
        })
        if label_col and numeric_cols:
            grouped = df.groupby(label_col)[numeric_cols[0]].sum().sort_values(ascending=False).head(10)
            charts.append({
                "type": "bar", "title": f"{numeric_cols[0]} by {label_col}",
                "labels": grouped.index.astype(str).tolist(),
                "datasets": [{"name": numeric_cols[0], "data": grouped.tolist()}],
            })
        if label_col and numeric_cols:
            grouped = df.groupby(label_col)[numeric_cols[0]].sum().sort_values(ascending=False).head(10)
            charts.append({
                "type": "pie", "title": f"{numeric_cols[0]} Distribution",
                "labels": grouped.index.astype(str).tolist(),
                "datasets": [{"name": numeric_cols[0], "data": grouped.tolist()}],
            })
        return charts


tool_registry.register(ChartTool())
