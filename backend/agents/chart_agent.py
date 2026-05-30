"""ChartAgent — wraps chart generation logic from main.py _generate_charts."""
import pandas as pd

from .base_agent import BaseAgent


class ChartAgent(BaseAgent):
    name = "ChartAgent"
    description = "图表生成与推荐"

    async def execute(self, context: dict) -> dict:
        df = context.get("df")
        if df is None:
            self.add_step(context, "error", "无可用数据生成图表")
            return context

        self.add_step(context, "running", "开始生成图表...")

        try:
            from main import _generate_charts
            charts = _generate_charts(df)
            context["charts"] = charts
            self.add_step(context, "done", f"图表生成完成: {len(charts)} 个图表")
        except Exception as e:
            self.add_step(context, "error", f"图表生成失败: {str(e)}")
            context.setdefault("errors", []).append(f"ChartAgent: {str(e)}")
            context["charts"] = []

        return context

    def suggest_charts(self, df: pd.DataFrame, data_summary: dict) -> list[dict]:
        """Recommend chart types based on column data types."""
        suggestions = []
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        str_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object"]

        if not numeric_cols:
            return suggestions

        suggestions.append({
            "type": "line", "title": "数据趋势",
            "reason": "数值列适合展示趋势变化",
            "columns": numeric_cols[:3],
        })

        if str_cols and numeric_cols:
            suggestions.append({
                "type": "bar", "title": "分类统计",
                "reason": f"按 {str_cols[0]} 分组查看 {numeric_cols[0]} 分布",
                "columns": [str_cols[0], numeric_cols[0]],
            })

        if str_cols and numeric_cols:
            suggestions.append({
                "type": "pie", "title": "占比分布",
                "reason": "查看各分类占比情况",
                "columns": [str_cols[0], numeric_cols[0]],
            })

        return suggestions
