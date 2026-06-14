"""ReportAgent — wraps workflow.generate_report for final report generation."""
import json
import re
import os
import httpx

from .base_agent import BaseAgent

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class ReportAgent(BaseAgent):
    name = "ReportAgent"
    description = "分析报告生成"

    async def execute(self, context: dict) -> dict:
        self.add_step(context, "running", "开始生成分析报告...")

        api_key = context.get("api_key", os.getenv("DEEPSEEK_API_KEY", ""))
        if not api_key:
            self.add_step(context, "error", "未配置 API Key，无法生成报告")
            context.setdefault("errors", []).append("ReportAgent: 未配置 DEEPSEEK_API_KEY")
            return context

        try:
            report = await self.generate_report(context, api_key)
            context["report"] = report
            self.add_step(context, "done", "分析报告生成完成")
        except Exception as e:
            self.add_step(context, "error", f"报告生成失败: {str(e)}")
            context.setdefault("errors", []).append(f"ReportAgent: {str(e)}")
            context["report"] = f"报告生成失败: {str(e)}"

        return context

    async def generate_report(self, context: dict, api_key: str) -> str:
        """Generate a professional analysis report from context data."""
        analysis = context.get("analysis", {})
        audit = context.get("audit_result", {})
        charts = context.get("charts", [])
        data_summary = context.get("data_summary", {})
        user_message = context.get("user_message", "")

        sections = []
        if analysis:
            summary_text = analysis.get("summary", "") if isinstance(analysis, dict) else str(analysis)
            anomaly_text = analysis.get("anomaly", "") if isinstance(analysis, dict) else ""
            trend_text = analysis.get("trend", "") if isinstance(analysis, dict) else ""
            sections.append(f"## 数据总结\n{summary_text}")
            if anomaly_text:
                sections.append(f"## 异常分析\n{anomaly_text}")
            if trend_text:
                sections.append(f"## 趋势分析\n{trend_text}")

        if audit:
            sections.append(f"## 数据审计\n{audit.get('quality_report', '')}")

        if charts:
            chart_types = set(c.get("type", "") for c in charts)
            sections.append(f"## 图表\n已生成 {len(charts)} 个图表 ({', '.join(chart_types)})")

        prompt = f"""根据以下数据，生成一份专业的数据分析报告。用中文，Markdown格式。

## 用户需求
{user_message}

## 数据信息
- 行列: {data_summary.get('shape', {}).get('rows', 0)}行 × {data_summary.get('shape', {}).get('columns', 0)}列
- 列名: {data_summary.get('columns', [])}

## 分析内容
{chr(10).join(sections)}

## 要求
- 结构清晰，包含：概述、关键发现、详细分析、建议
- 用数据说话，引用具体数值
- 500字以内"""

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
                    "temperature": 0.5,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# T27: register with agent registry
from .registry import registry
registry.register("ReportAgent", ReportAgent)
