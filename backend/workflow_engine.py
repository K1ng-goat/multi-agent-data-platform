"""Workflow Engine — manages Shared Context and orchestrates the Multi-Agent pipeline."""
import os
import json
import sys
from agents.data_master_agent import DataMasterAgent

# 500KB response limit
MAX_RESPONSE_BYTES = 500 * 1024


class WorkflowEngine:
    """Orchestrates the full multi-agent execution pipeline."""

    def create_context(self, session_id: str, user_message: str, df, data_summary: dict,
                       api_key: str = "") -> dict:
        """Initialize the Shared Context dict that flows through all agents."""
        return {
            "session_id": session_id,
            "user_message": user_message,
            "intent": "",
            "df": df,
            "data_summary": data_summary,
            "analysis": None,
            "charts": None,
            "audit_result": None,
            "style": None,
            "report": None,
            "exports": None,
            "steps": [],
            "errors": [],
            "api_key": api_key or os.getenv("DEEPSEEK_API_KEY", ""),
        }

    async def run(self, user_message: str, session: dict, session_id: str) -> dict:
        """Execute the full multi-agent pipeline and return formatted response."""
        df = session.get("df")
        data_summary = session.get("data_summary", {})

        # Build context
        context = self.create_context(
            session_id=session_id,
            user_message=user_message,
            df=df,
            data_summary=data_summary,
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        )

        # Carry forward style preferences and memory context from the session
        context.setdefault("active_theme", session.get("active_theme", "business"))
        context.setdefault("style_overrides", session.get("style_overrides", {}))
        context["memory_context"] = session.get("_memory_context", "")

        # Run Master Agent (which cascades to all sub-agents)
        master = DataMasterAgent()
        context = await master.execute(context)

        # CRITICAL: remove non-serializable objects before formatting
        context.pop("df", None)
        context.pop("_df", None)

        return self.format_response(context)

    def format_response(self, context: dict) -> dict:
        """Convert the shared context into a frontend-friendly, lightweight response dict."""
        # Build reply with length limits
        reply_parts = []
        MAX_SECTION = 5000  # max chars per section

        analysis = context.get("analysis")
        if analysis:
            if isinstance(analysis, dict):
                summary = (analysis.get("summary", "") or "")[:MAX_SECTION]
                anomaly = (analysis.get("anomaly", "") or "")[:MAX_SECTION]
                trend = (analysis.get("trend", "") or "")[:MAX_SECTION]
                if summary:
                    reply_parts.append(f"## 数据总结\n{summary}")
                if anomaly:
                    reply_parts.append(f"## 异常分析\n{anomaly}")
                if trend:
                    reply_parts.append(f"## 趋势分析\n{trend}")
            elif isinstance(analysis, str):
                reply_parts.append(analysis[:MAX_SECTION])

        audit = context.get("audit_result")
        if audit and isinstance(audit, dict):
            qr = (audit.get("quality_report", "") or "")[:MAX_SECTION]
            if qr:
                reply_parts.append(f"\n## 数据审计\n{qr}")

        report = context.get("report")
        if report and isinstance(report, str):
            reply_parts.append(f"\n{report[:MAX_SECTION]}")

        exports = context.get("exports")
        if exports and isinstance(exports, list):
            filenames = [e.get("filename", "") for e in exports[:20] if isinstance(e, dict)]
            if filenames:
                reply_parts.append(f"\n## 导出文件\n" + "\n".join(f"- {f}" for f in filenames))

        if not reply_parts:
            reply_parts.append("分析完成，详见执行步骤。")

        reply = "\n\n".join(reply_parts)
        # Hard cap on total reply
        reply = reply[:100000]

        # Lightweight steps: keep only last 50, truncate messages
        all_steps = context.get("steps", [])
        if isinstance(all_steps, list):
            steps = []
            for s in all_steps[-50:]:
                if isinstance(s, dict):
                    steps.append({
                        "agent": str(s.get("agent", ""))[:30],
                        "status": str(s.get("status", "done"))[:10],
                        "message": (s.get("message", "") or "")[:200],
                    })
        else:
            steps = []

        # Charts: strip to titles only (no full data arrays)
        raw_charts = context.get("charts")
        charts: list = []
        if isinstance(raw_charts, list):
            for c in raw_charts[:6]:
                if isinstance(c, dict):
                    charts.append({
                        "type": c.get("type", ""),
                        "title": (c.get("title", "") or "")[:60],
                    })

        # Exports: strip to filenames
        raw_exports = context.get("exports")
        exports: list = []
        if isinstance(raw_exports, list):
            for e in raw_exports[:10]:
                if isinstance(e, dict):
                    exports.append({"type": e.get("type", ""), "filename": e.get("filename", "")[:120]})

        # Errors: keep only last 20
        raw_errors = context.get("errors", [])
        errors = [str(e)[:200] for e in (raw_errors or [])[-20:]]

        intent = context.get("intent", "analyze")
        mode = "workflow" if intent in ("full_report", "analyze_and_report") else "chat"

        result = {
            "mode": mode,
            "reply": reply,
            "steps": steps,
            "intent": intent,
            "charts": charts,
            "exports": exports,
            "errors": errors,
        }

        if context.get("style"):
            result["style_applied"] = True
            result["active_theme"] = context.get("active_theme", "business")

        # Size check
        try:
            size = len(json.dumps(result, ensure_ascii=False, default=str))
            print(f"[WorkflowEngine] format_response size: {size} bytes ({size / 1024:.1f} KB)")
            if size > MAX_RESPONSE_BYTES:
                print(f"[WorkflowEngine] WARNING: response exceeds {MAX_RESPONSE_BYTES} bytes, truncating reply")
                result["reply"] = result["reply"][:10000]
                result["steps"] = result["steps"][:20]
                result["charts"] = []
                result["exports"] = []
                size2 = len(json.dumps(result, ensure_ascii=False, default=str))
                print(f"[WorkflowEngine] after truncation: {size2} bytes")
        except Exception:
            print("[WorkflowEngine] WARNING: unable to measure response size")

        return result

    async def run_chat(self, user_message: str, session: dict, session_id: str) -> dict:
        """Lightweight single-agent execution for simple chat queries."""
        context = self.create_context(
            session_id=session_id,
            user_message=user_message,
            df=session.get("df"),
            data_summary=session.get("data_summary", {}),
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        )
        context.setdefault("active_theme", session.get("active_theme", "business"))
        context.setdefault("style_overrides", session.get("style_overrides", {}))

        from agents.data_agent import DataAgent
        agent = DataAgent()
        context = await agent.execute(context)

        # CRITICAL: remove non-serializable objects before formatting
        context.pop("df", None)
        context.pop("_df", None)

        return self.format_response(context)
