"""AgentOrchestrator — extracts /analyze business logic into an agent pipeline.

Refactor (T23): the /analyze endpoint previously contained 200+ lines of
inline pandas data prep, chart generation, AI analysis, dashboard/report
persistence, and memory save.  That logic now lives here, so the route
layer is thin: validate → orchestrate → return.
"""
from __future__ import annotations
import os
import io
import json
import re
import uuid
import time
import traceback
import pandas as pd
import httpx

import config
import dashboard_service as ds
from memory.memory_manager import get_memory_manager
from database import SessionLocal
import preference_model
from workflow_trace import trace_store, WorkflowTrace  # T30
from .evaluator import evaluator                         # T35
from prompt.prompt_manager import prompt_manager           # T36
from knowledge.retriever import retriever                   # T43

DEEPSEEK_BASE_URL = config.DEEPSEEK_BASE_URL


class AgentOrchestrator:
    """Orchestrates the full analysis pipeline from raw Excel bytes to structured result.

    The route layer only calls :meth:`run_analysis_pipeline` and returns
    its result — all business logic is encapsulated here.
    """

    # ── Public API ──────────────────────────────────────────

    async def run_analysis_pipeline(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: int,
        api_key: str = "",
        sessions: dict | None = None,
        session_store=None,
        plan=None,          # T24: explicit plan (overrides auto-planner)
        user_intent: str = "",   # T24: intent string for auto-planning
        memory_context=None,     # T25: MemoryContext from MemoryRouter
    ) -> dict:
        """Run the complete analysis pipeline and return a frontend-compatible result.

        If ``plan`` is provided, only enabled steps execute.  If ``user_intent``
        is provided without a plan, the PlannerAgent auto-generates one from
        the data.  If ``memory_context`` is provided (T25), it is injected into
        the analysis prompt for context-aware results.
        """
        # 1. Parse Excel
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        print(f"[Orchestrator] Excel loaded — shape={df.shape}")

        # 2. Date conversion
        df = _convert_excel_dates(df)

        # 3. Build data summary
        data_summary = _build_data_summary(filename, df)
        session_id = uuid.uuid4().hex[:12]

        # T30: Start workflow trace
        trace = trace_store.start_trace(session_id)
        t0 = time.time()

        # T24: Auto-plan from data if intent given but no explicit plan
        if plan is None and user_intent:
            from agents.planner_agent import PlannerAgent
            p = PlannerAgent()
            plan = p.plan(data_summary, user_intent)
            print(f"[Orchestrator] auto-plan generated from intent={user_intent}")
            trace.add_step("PlannerAgent", True, (time.time() - t0) * 1000)

        # 4. Create in-memory session
        if sessions is not None:
            sessions[session_id] = {
                "df": df,
                "data_summary": data_summary,
                "history": [],
                "analysis": {},
                "charts": [],
                "session_id": session_id,
                "active_theme": "business",
                "style_overrides": {},
            }
            _load_preferences(sessions[session_id], user_id)

        # 5. Chart generation (T24: conditional on plan)
        charts: list = []
        tc0 = time.time()
        if plan is None or plan.run_charts:
            charts = _generate_charts(df)
            print(f"[Orchestrator] charts={len(charts)}")
            trace.add_step("ChartAgent", True, (time.time() - tc0) * 1000, "ChartTool")
        else:
            print("[Orchestrator] charts skipped (plan)")

        # 6. AI analysis or fallback (T24: conditional on plan)
        ta0 = time.time()
        if plan is not None and not plan.run_kpi:
            analysis_result = {"summary": "", "anomaly": "", "trend": ""}
            print("[Orchestrator] AI analysis skipped (plan)")
        elif not api_key:
            analysis_result = {
                "summary": "未配置 DEEPSEEK_API_KEY 环境变量，无法进行 AI 分析。",
                "anomaly": "请在终端执行: `$env:DEEPSEEK_API_KEY='your_key'` 后重新上传文件。",
                "trend": "",
            }
            trace.add_step("DataAgent", True, (time.time() - ta0) * 1000, "ExcelTool")
        else:
            analysis_result = await _ai_analyze(data_summary, api_key, memory_context)
            trace.add_step("DataAgent", True, (time.time() - ta0) * 1000, "ExcelTool")
            evaluator.evaluate("DataAgent", analysis_result, {"intent": user_intent})

        if sessions is not None:
            sessions[session_id]["analysis"] = analysis_result
            sessions[session_id]["charts"] = charts

        # 6. Persist — dashboard, reports, memory, session store
        _persist_dashboard(session_id, data_summary, analysis_result, charts, user_id)
        _persist_memory(user_id, session_id, filename, data_summary, charts,
                        analysis_result, sessions[session_id] if sessions else {})

        if sessions is not None and session_store is not None:
            try:
                session_store.save(session_id, user_id, sessions[session_id])
                print("[Orchestrator] SessionStore save OK")
            except Exception:
                print("[Orchestrator] ERROR in session_store.save:")
                traceback.print_exc()

        # T30: Save workflow trace
        trace_store.save(trace)

        print(f"[Orchestrator] pipeline complete — session={session_id} "
              f"trace={trace.workflow_id} steps={len(trace.steps)}")
        return {
            "session_id": session_id,
            "data_summary": data_summary,
            "charts": charts,
            "analysis": analysis_result,
        }


# ── Internal helpers (extracted from main.py) ──────────────

def _build_data_summary(filename: str, df: pd.DataFrame) -> dict:
    return {
        "filename": filename,
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": df.columns.tolist(),
        "dtypes": {k: str(v) for k, v in df.dtypes.to_dict().items()},
        "describe": df.describe(include="all").fillna("").to_dict(),
        "sample": df.head(20).fillna("").to_dict(orient="records"),
        "null_counts": {k: int(v) for k, v in df.isnull().sum().to_dict().items()},
    }


def _load_preferences(session: dict, user_id: int) -> None:
    db = SessionLocal()
    try:
        theme_row = db.query(preference_model.UserPreference).filter(
            preference_model.UserPreference.key == "active_theme",
            preference_model.UserPreference.user_id == user_id,
        ).first()
        if theme_row:
            try:
                session["active_theme"] = json.loads(theme_row.value)
            except (json.JSONDecodeError, TypeError):
                pass
        overrides_row = db.query(preference_model.UserPreference).filter(
            preference_model.UserPreference.key == "style_overrides",
            preference_model.UserPreference.user_id == user_id,
        ).first()
        if overrides_row:
            try:
                session["style_overrides"] = json.loads(overrides_row.value)
            except (json.JSONDecodeError, TypeError):
                pass
    finally:
        db.close()


async def _ai_analyze(data_summary: dict, api_key: str,
                      memory_context=None) -> dict:
    print("[Orchestrator] DeepSeek analysis starting")

    # T25: inject memory context if available
    memory_prefix = ""
    if memory_context and not memory_context.is_empty:
        parts = []
        prefs = memory_context.user_preferences
        if prefs:
            parts.append(f"[User Preferences] {prefs}")
        if memory_context.conversation_summary:
            parts.append(f"[Recent Context] {memory_context.conversation_summary}")
        if memory_context.analysis_history:
            files = [a.get("filename","") for a in memory_context.analysis_history[:3]]
            parts.append(f"[Previously Analyzed] {files}")
        if parts:
            memory_prefix = "\n".join(parts) + "\n\n"

    # T36: Use prompt template (fallback to hardcoded if template missing)
    base_prompt = prompt_manager.get(
        "data_analysis",
        filename=data_summary.get("filename", ""),
        rows=data_summary.get("shape", {}).get("rows", 0),
        columns=data_summary.get("shape", {}).get("columns", 0),
        columns_list=data_summary.get("columns", []),
        dtypes=json.dumps(data_summary.get("dtypes", {}), ensure_ascii=False),
        describe=json.dumps(data_summary.get("describe", {}), ensure_ascii=False),
        sample=json.dumps(data_summary.get("sample", []), ensure_ascii=False),
        null_counts=json.dumps(data_summary.get("null_counts", {}), ensure_ascii=False),
    )
    if not base_prompt:
        # Fallback for empty template
        base_prompt = f"You are a data analyst. Analyze this Excel data. Columns: {data_summary.get('columns',[])}. Return JSON with summary, anomaly, trend."

    # T43: Inject retrieved knowledge into the prompt
    knowledge_context = retriever.retrieve_for_prompt(
        ", ".join(str(c) for c in data_summary.get("columns", [])[:3])
    )

    prompt = memory_prefix + knowledge_context + base_prompt

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
        print(f"[Orchestrator] DeepSeek status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"[Orchestrator] DeepSeek error: {resp.text}")
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


def _persist_dashboard(session_id: str, data_summary: dict,
                       analysis: dict, charts: list, user_id: int) -> None:
    try:
        ds.update_snapshot(session_id, data_summary, analysis, charts, user_id)
        print("[Orchestrator] dashboard/report saved")
    except Exception:
        print("[Orchestrator] ERROR in dashboard save:")
        traceback.print_exc()


def _persist_memory(user_id: int, session_id: str, filename: str,
                    data_summary: dict, charts: list, analysis: dict,
                    session: dict) -> None:
    try:
        mgr = get_memory_manager()
        mgr.save_workspace(user_id, session_id, filename,
                           data_summary, charts, analysis,
                           session.get("active_theme", "business"))
        mgr.save_analysis_memory(user_id, session_id, filename,
                                 analysis, charts)
        print("[Orchestrator] memory saved")
    except Exception:
        print("[Orchestrator] ERROR saving memory:")
        traceback.print_exc()


# ── Reused from main.py (unchanged logic) ──────────────────

def _convert_excel_dates(df: pd.DataFrame) -> pd.DataFrame:
    date_keywords = ["date", "日期", "时间", "time", "year", "month", "day",
                     "年", "月", "日", "created", "updated", "modified", "创建", "修改"]
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue
        col_lower = str(col).lower()
        has_date_name = any(kw in col_lower for kw in date_keywords)
        mn, mx = s.min(), s.max()
        if has_date_name:
            is_date_col = 1 <= mn <= 200000 and 1 <= mx <= 200000
        else:
            is_date_col = 30000 <= mn <= 200000 and 30000 <= mx <= 200000
        if is_date_col:
            try:
                converted = pd.to_datetime(df[col], origin="1899-12-30", unit="D", errors="coerce")
                valid_ratio = converted.notna().sum() / len(s)
                if valid_ratio > 0.8:
                    df[col] = converted.dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return df


def _generate_charts(df: pd.DataFrame) -> list[dict]:
    charts = []
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        return charts
    str_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object"]
    date_cols = [c for c in str_cols if any(kw in str(c).lower() for kw in
                 ["date", "日期", "时间", "time", "year", "month", "day", "年", "月", "日", "created"])]
    label_col = None
    if date_cols:
        label_col = date_cols[0]
    elif str_cols:
        candidates = [(c, df[c].nunique()) for c in str_cols if df[c].nunique() <= 50]
        if candidates:
            label_col = min(candidates, key=lambda x: x[1])[0]
    head = df.head(50)
    if label_col:
        labels = head[label_col].astype(str).tolist()
    else:
        labels = [str(i + 1) for i in range(len(head))]
    charts.append({
        "type": "line", "title": "数据趋势", "labels": labels,
        "datasets": [{"name": col, "data": head[col].fillna(0).tolist()} for col in numeric_cols[:3]],
    })
    if label_col and numeric_cols:
        grouped = df.groupby(label_col)[numeric_cols[0]].sum().sort_values(ascending=False)
        top = grouped.head(10)
        charts.append({
            "type": "bar", "title": f"{numeric_cols[0]} 分类统计",
            "labels": top.index.astype(str).tolist(),
            "datasets": [{"name": numeric_cols[0], "data": top.tolist()}],
        })
    if label_col and numeric_cols:
        grouped = df.groupby(label_col)[numeric_cols[0]].sum().sort_values(ascending=False)
        top = grouped.head(10)
        charts.append({
            "type": "pie", "title": f"{numeric_cols[0]} 占比分布",
            "labels": top.index.astype(str).tolist(),
            "datasets": [{"name": numeric_cols[0], "data": top.tolist()}],
        })
    return charts
