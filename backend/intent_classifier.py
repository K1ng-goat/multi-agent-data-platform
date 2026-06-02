"""Unified intent classifier — single source of truth.

Previously two independent implementations existed:
  - main.py::_classify_intent         (20 lines, returns "workflow" | "chat")
  - DataMasterAgent::classify_intent  (40 lines, returns 8 intent strings)

Both used duplicate keyword lists.  This module merges them:
  - classify()             → 9 intents for Agent routing
  - classify_for_chat()    → "workflow" | "chat" for /chat compatibility
"""

# ── Keyword lists ──────────────────────────────────────────

WORKFLOW_KEYWORDS = [
    "报告", "日报", "周报", "月报", "生成", "完整分析",
    "全面分析", "经营分析", "综合分析", "总结报告", "汇总",
    "深度分析", "复盘", "帮我分析", "做分析", "出报告",
    "经营情况", "整体分析", "分析报告", "全面评估", "综合评估",
    "report", "generate", "analyze the", "summarize", "full analysis",
]

FULL_REPORT_KEYWORDS = [
    "完整报告", "全面报告", "综合报告", "生成报告", "出报告",
    "分析报告", "最终报告", "完整分析报告",
]

STYLE_KEYWORDS = [
    "风格", "主题", "字体", "颜色", "样式", "黑体", "宋体",
    "商务", "简洁", "深色", "学术",
]

CHART_KEYWORDS = [
    "图表", "画图", "生成图", "柱状图", "折线图", "饼图",
    "chart", "可视化",
]

AUDIT_KEYWORDS = [
    "审计", "检查", "质量", "空值", "重复", "异常值", "数据质量",
]

EXPORT_KEYWORDS = [
    "导出", "下载", "export", "保存",
]

# Keywords whose presence alongside style/chart/audit/export keywords
# indicates the request is NOT a single-task request → fall through to workflow.
DATA_ANALYSIS_KEYWORDS = [
    "分析", "数据", "图表", "统计",
]


# ── Intent constants ───────────────────────────────────────

class Intent:
    FULL_REPORT = "full_report"
    ANALYZE = "analyze"
    CHART = "chart"
    AUDIT = "audit"
    REPORT = "report"
    STYLE = "style"
    EXPORT = "export"
    DATA_WITH_CHARTS = "data_with_charts"
    ANALYZE_AND_REPORT = "analyze_and_report"


# ── Public API ─────────────────────────────────────────────

def classify(user_message: str) -> str:
    """Classify user intent into one of 9 values used by the Agent router.

    Behaviour is byte-for-byte identical to the old
    DataMasterAgent.classify_intent().  All keyword lists and control-flow
    order are preserved exactly.
    """
    q = user_message.lower()

    # 1. Full report — most comprehensive
    for kw in FULL_REPORT_KEYWORDS:
        if kw in q:
            return Intent.FULL_REPORT

    # 2. Style-only
    if _has_any(q, STYLE_KEYWORDS) and not _has_any(q, DATA_ANALYSIS_KEYWORDS):
        return Intent.STYLE

    # 3. Chart-only
    if _has_any(q, CHART_KEYWORDS) and not _has_any(q, WORKFLOW_KEYWORDS):
        return Intent.CHART

    # 4. Audit-only
    if _has_any(q, AUDIT_KEYWORDS) and not _has_any(q, WORKFLOW_KEYWORDS):
        return Intent.AUDIT

    # 5. Export-only
    if _has_any(q, EXPORT_KEYWORDS) and not _has_any(q, WORKFLOW_KEYWORDS):
        return Intent.EXPORT

    # 6. General workflow / analyze_and_report
    for kw in WORKFLOW_KEYWORDS:
        if kw.lower() in q:
            return Intent.ANALYZE_AND_REPORT

    # 7. Long question heuristic
    if len(user_message) > 40:
        return Intent.ANALYZE_AND_REPORT

    # 8. Default → analyze
    return Intent.ANALYZE


def classify_for_chat(user_message: str) -> str:
    """Compatibility wrapper — same interface as old main._classify_intent.

    Only full_report and analyze_and_report trigger the workflow pipeline;
    everything else (including the default "analyze" fallback) routes to
    the /chat tool-calling pipeline, matching the old behaviour exactly.
    """
    intent = classify(user_message)
    if intent in (Intent.FULL_REPORT, Intent.ANALYZE_AND_REPORT):
        return "workflow"
    return "chat"


# ── Internal helpers ───────────────────────────────────────

def _has_any(text: str, keywords: list[str]) -> bool:
    """Return True if any keyword appears in text."""
    return any(kw in text for kw in keywords)
