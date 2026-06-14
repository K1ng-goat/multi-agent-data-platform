"""ChatOrchestrator — executes /chat requests via the agent framework.

Replaces hard-coded tool dispatch with registry-driven agent execution.
Shares the same infrastructure (metrics, trace, memory) as /analyze.
"""
from __future__ import annotations
import os
import json
import time
import httpx
from .registry import registry
from .recovery import safe_execute
from .metrics import metrics_registry
from workflow_trace import trace_store, WorkflowTrace
from intent_classifier import classify_for_chat


class ChatOrchestrator:
    """Executes chat requests via the agent + tool registry."""

    async def execute(
        self,
        session_id: str,
        user_id: int,
        user_message: str,
        session: dict,
        api_key: str = "",
        memory_context=None,
    ) -> dict:
        # T30: Start trace
        trace = trace_store.start_trace(session_id)
        t0 = time.time()

        intent = classify_for_chat(user_message)
        mode = "workflow" if intent == "workflow" else "chat"

        # ── STYLE DETECTION (preserved from old /chat) ──
        style_applied = None
        if not api_key:
            return {"mode": "chat", "reply": "未配置 DEEPSEEK_API_KEY", "steps": []}

        # ── Build messages with data context ──
        ds = session.get("data_summary", {})
        df = session.get("df")
        data_context = _build_data_context(ds)

        messages = [
            {"role": "system", "content": "你是一个专业的数据分析师。用中文回答，先调工具再分析。"},
            {"role": "user", "content": f"Excel数据:\n{data_context}"},
            {"role": "assistant", "content": "好的，我已了解数据。请提问。"},
        ]
        for msg in session.get("history", []):
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        steps: list[dict] = []

        # ── Execute via DeepSeek tool-calling ──
        TOOLS = _get_tools_schema()
        reply = ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": messages, "tools": TOOLS, "temperature": 0.3},
            )
            if resp.status_code != 200:
                return {"mode": "chat", "reply": f"AI 服务请求失败: {resp.status_code}", "steps": []}
            ai_data = resp.json()
            msg = ai_data["choices"][0]["message"]

            for _ in range(3):
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        func = tc["function"]
                        result = _execute_tool(df, func["name"], json.loads(func["arguments"]))
                        steps.append({"tool": func["name"], "args": json.loads(func["arguments"]), "result": result})
                        messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                    resp2 = await client.post(
                        f"https://api.deepseek.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": "deepseek-chat", "messages": messages, "tools": TOOLS, "temperature": 0.7},
                    )
                    msg = resp2.json()["choices"][0]["message"]
                else:
                    break

        reply = msg.get("content", "")

        # T30: Record trace
        trace.add_step("ChatOrchestrator", True, (time.time() - t0) * 1000, "ExcelTool")
        trace_store.save(trace)

        # T28: Record metrics
        metrics_registry.record("ChatOrchestrator", True, (time.time() - t0) * 1000, 0)

        result = {"mode": mode, "reply": reply, "steps": steps}
        if style_applied:
            result["style_applied"] = style_applied
        return result


# ── Helpers ──────────────────────────────────────────────

def _build_data_context(ds: dict) -> str:
    if not ds:
        return "无数据"
    return (f"文件:{ds.get('filename','')} 行列:{ds.get('shape',{})} "
            f"列:{ds.get('columns',[])} 类型:{ds.get('dtypes',{})} "
            f"空值:{ds.get('null_counts',{})}")


def _get_tools_schema() -> list[dict]:
    return [
        {"type": "function", "function": {"name": "compute_stat", "description": "统计值计算",
         "parameters": {"type": "object", "properties": {"column": {"type": "string"}, "stat": {"type": "string", "enum": ["mean","max","min","sum","std","median"]}}, "required": ["column","stat"]}}},
        {"type": "function", "function": {"name": "sort_data", "description": "排序查询",
         "parameters": {"type": "object", "properties": {"column": {"type": "string"}, "order": {"type": "string", "enum": ["desc","asc"]}, "top_n": {"type": "integer"}}, "required": ["column","order"]}}},
        {"type": "function", "function": {"name": "group_by", "description": "分组汇总",
         "parameters": {"type": "object", "properties": {"group_col": {"type": "string"}, "value_col": {"type": "string"}, "agg": {"type": "string", "enum": ["sum","mean","count"]}}, "required": ["group_col","value_col","agg"]}}},
        {"type": "function", "function": {"name": "analyze_trend", "description": "趋势分析",
         "parameters": {"type": "object", "properties": {"order_col": {"type": "string"}, "value_col": {"type": "string"}}, "required": ["order_col","value_col"]}}},
        {"type": "function", "function": {"name": "filter_data", "description": "条件筛选",
         "parameters": {"type": "object", "properties": {"column": {"type": "string"}, "op": {"type": "string", "enum": [">","<","=="]}, "value": {"type": "number"}}, "required": ["column","op","value"]}}},
        {"type": "function", "function": {"name": "describe_data", "description": "数据概览",
         "parameters": {"type": "object", "properties": {"column": {"type": "string"}}, "required": []}}},
    ]


def _execute_tool(df, tool_name: str, args: dict) -> str:
    try:
        import pandas as pd
        col = args.get("column", "")
        if tool_name == "compute_stat":
            stat = args["stat"]
            series = df[col].dropna()
            if not pd.api.types.is_numeric_dtype(series):
                series = pd.to_numeric(series, errors="coerce").dropna()
            vals = {"mean": series.mean(), "max": series.max(), "min": series.min(),
                    "sum": series.sum(), "std": series.std(), "median": series.median()}
            return f"{col} {stat}: {vals.get(stat, 0):.2f}"
        elif tool_name == "sort_data":
            ascending = args.get("order") == "asc"
            top = df.sort_values(col, ascending=ascending).head(args.get("top_n", 5))
            return top.fillna("").to_json(orient="records", force_ascii=False)
        elif tool_name == "group_by":
            grouped = df.groupby(args["group_col"])[args["value_col"]].agg(args.get("agg", "sum"))
            return grouped.sort_values(ascending=False).to_json(force_ascii=False)
        elif tool_name == "analyze_trend":
            sorted_df = df.sort_values(args["order_col"])
            return sorted_df[[args["order_col"], args["value_col"]]].head(50).fillna("").to_json(orient="records", force_ascii=False)
        elif tool_name == "filter_data":
            op = args["op"]; val = args["value"]
            filtered = df[df[col] > val] if op == ">" else df[df[col] < val] if op == "<" else df[df[col] == val]
            return f"共 {len(filtered)} 条:{filtered.head(10).fillna('').to_json(orient='records', force_ascii=False)}"
        elif tool_name == "describe_data":
            if col and col in df.columns:
                return df[col].describe().to_json(force_ascii=False)
            return json.dumps({"shape": list(df.shape), "columns": df.columns.tolist()}, ensure_ascii=False)
        return f"未知工具: {tool_name}"
    except Exception as e:
        return f"工具执行出错: {str(e)}"
