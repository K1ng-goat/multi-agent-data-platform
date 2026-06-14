"""DataAgent — wraps data analysis, statistics, and DeepSeek AI analysis logic."""
import json
import os
import re
import httpx
import pandas as pd

from .base_agent import BaseAgent

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DataAgent(BaseAgent):
    name = "DataAgent"
    description = "数据分析与统计计算"

    async def execute(self, context: dict) -> dict:
        df = context.get("df")
        if df is None:
            self.add_step(context, "error", "无可用数据")
            return context

        self.add_step(context, "running", "开始数据分析...")

        # 1. Generate data summary
        data_summary = self.summarize(df, context)
        context["data_summary"] = data_summary
        self.add_step(context, "done", f"数据摘要完成: {data_summary.get('shape', {}).get('rows', 0)}行 × {data_summary.get('shape', {}).get('columns', 0)}列")

        # 2. Convert Excel serial dates
        from main import _convert_excel_dates
        df = _convert_excel_dates(df)
        context["df"] = df

        # 3. AI analysis via DeepSeek
        api_key = context.get("api_key", os.getenv("DEEPSEEK_API_KEY", ""))
        if api_key:
            try:
                analysis = await self._ai_analyze(df, data_summary, api_key)
                context["analysis"] = analysis
                self.add_step(context, "done", "AI分析完成")
            except Exception as e:
                self.add_step(context, "error", f"AI分析失败: {str(e)}")
                context.setdefault("errors", []).append(f"DataAgent AI分析: {str(e)}")
                context["analysis"] = {
                    "summary": "AI分析失败，请检查 API Key 配置。",
                    "anomaly": "", "trend": "",
                }
        else:
            self.add_step(context, "done", "未配置 API Key，跳过AI分析")
            context["analysis"] = {
                "summary": "未配置 DEEPSEEK_API_KEY，无法进行 AI 分析。",
                "anomaly": "", "trend": "",
            }

        return context

    def summarize(self, df: pd.DataFrame, context: dict) -> dict:
        """Generate a data summary dict from the DataFrame."""
        from main import _convert_excel_dates
        df_conv = _convert_excel_dates(df.copy())
        return {
            "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
            "columns": df.columns.tolist(),
            "dtypes": {k: str(v) for k, v in df.dtypes.to_dict().items()},
            "describe": df.describe(include="all").fillna("").to_dict(),
            "sample": df_conv.head(20).fillna("").to_dict(orient="records"),
            "null_counts": {k: int(v) for k, v in df.isnull().sum().to_dict().items()},
        }

    async def _ai_analyze(self, df: pd.DataFrame, data_summary: dict, api_key: str) -> dict:
        """Call DeepSeek for AI analysis (reuses /analyze prompt logic)."""
        prompt = f"""You are a data analyst. Analyze this Excel data and provide insights in Chinese.

Data Summary:
- Shape: {data_summary['shape']['rows']} rows × {data_summary['shape']['columns']} columns
- Columns: {data_summary['columns']}
- Data Types: {json.dumps(data_summary['dtypes'], ensure_ascii=False)}
- Statistical Summary: {json.dumps(data_summary['describe'], ensure_ascii=False)}
- Sample Data (first 20 rows): {json.dumps(data_summary['sample'], ensure_ascii=False)}
- Null Value Counts: {json.dumps(data_summary['null_counts'], ensure_ascii=False)}

Please return ONLY a JSON object (no markdown, no code block) in this exact format:
{{"summary": "数据总结...", "anomaly": "异常分析...", "trend": "趋势分析..."}}
Keep each section within 150-200 Chinese characters."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            ai_data = resp.json()

        content = ai_data["choices"][0]["message"]["content"]
        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", content)
            analysis = json.loads(m.group()) if m else {"summary": content, "anomaly": "", "trend": ""}

        return {
            "summary": analysis.get("summary", ""),
            "anomaly": analysis.get("anomaly", ""),
            "trend": analysis.get("trend", ""),
        }


# T27: register with agent registry
from .registry import registry
registry.register("DataAgent", DataAgent)
