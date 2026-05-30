"""Master Agent — intent classification, task planning, agent routing, pipeline execution."""
from .base_agent import BaseAgent
from .data_agent import DataAgent
from .chart_agent import ChartAgent
from .audit_agent import AuditAgent
from .report_agent import ReportAgent
from .style_agent import StyleAgent
from .export_agent import ExportAgent

# Intent → agent routing map
INTENT_AGENT_MAP: dict[str, list[str]] = {
    "analyze": ["DataAgent"],
    "chart": ["ChartAgent"],
    "audit": ["AuditAgent"],
    "report": ["ReportAgent"],
    "style": ["StyleAgent"],
    "export": ["ExportAgent"],
    "full_report": ["DataAgent", "AuditAgent", "ChartAgent", "ReportAgent", "StyleAgent", "ExportAgent"],
    "data_with_charts": ["DataAgent", "ChartAgent"],
    "analyze_and_report": ["DataAgent", "ReportAgent"],
}

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

AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "DataAgent": DataAgent,
    "ChartAgent": ChartAgent,
    "AuditAgent": AuditAgent,
    "ReportAgent": ReportAgent,
    "StyleAgent": StyleAgent,
    "ExportAgent": ExportAgent,
}


class DataMasterAgent(BaseAgent):
    name = "MasterAgent"
    description = "主控Agent — 意图分析、任务拆分、Agent调度、结果合并"

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def _get_agent(self, name: str) -> BaseAgent:
        if name not in self._agents:
            self._agents[name] = AGENT_CLASSES[name]()
        return self._agents[name]

    async def execute(self, context: dict) -> dict:
        user_message = context.get("user_message", "")
        self.add_step(context, "running", f"Master Agent 分析意图: {user_message[:50]}...")

        # Step 0: Inject memory context if available
        memory_ctx = context.get("memory_context", "")
        if memory_ctx:
            self.add_step(context, "done", f"Memory注入: {memory_ctx[:80]}...")
            # Prepend memory to user_message so agents can reference it
            context["user_message"] = f"[记忆上下文]\n{memory_ctx}\n\n[当前请求]\n{user_message}"

        # Step 1: Classify intent
        intent = self.classify_intent(user_message, context)
        context["intent"] = intent
        self.add_step(context, "done", f"意图识别: {intent}")

        # Step 2: Plan tasks
        tasks = self.plan_tasks(intent, context)
        agent_names = [t["agent"] for t in tasks]
        self.add_step(context, "done", f"任务规划: {' → '.join(agent_names)}")

        # Step 3: Execute pipeline
        context = await self.execute_pipeline(tasks, context)

        # Step 4: Merge results
        self.add_step(context, "done", "所有Agent执行完毕")
        return context

    def classify_intent(self, user_message: str, context: dict) -> str:
        """Classify user intent: full_report, workflow, analyze, chart, audit, style, export."""
        q = user_message.lower()

        # Check for full report first (most comprehensive)
        for kw in FULL_REPORT_KEYWORDS:
            if kw in q:
                return "full_report"

        # Style-only requests
        style_keywords = ["风格", "主题", "字体", "颜色", "样式", "黑体", "宋体", "商务", "简洁", "深色", "学术"]
        if any(kw in q for kw in style_keywords) and not any(kw in q for kw in ["分析", "数据", "图表", "统计"]):
            return "style"

        # Chart-only requests
        chart_keywords = ["图表", "画图", "生成图", "柱状图", "折线图", "饼图", "chart", "可视化"]
        if any(kw in q for kw in chart_keywords) and not any(kw in q for kw in WORKFLOW_KEYWORDS):
            return "chart"

        # Audit-only requests
        audit_keywords = ["审计", "检查", "质量", "空值", "重复", "异常值", "数据质量"]
        if any(kw in q for kw in audit_keywords) and not any(kw in q for kw in WORKFLOW_KEYWORDS):
            return "audit"

        # Export-only requests
        export_keywords = ["导出", "下载", "export", "保存"]
        if any(kw in q for kw in export_keywords) and not any(kw in q for kw in WORKFLOW_KEYWORDS):
            return "export"

        # General workflow / analyze (uses data + charts)
        for kw in WORKFLOW_KEYWORDS:
            if kw.lower() in q:
                return "analyze_and_report"

        # Long questions → analyze
        if len(user_message) > 40:
            return "analyze_and_report"

        # Default: analyze
        return "analyze"

    def plan_tasks(self, intent: str, context: dict) -> list[dict]:
        """Convert intent into an ordered agent task list."""
        agent_names = INTENT_AGENT_MAP.get(intent, ["DataAgent"])
        tasks = []
        for name in agent_names:
            agent = self._get_agent(name)
            tasks.append({
                "agent": name,
                "description": agent.description,
            })
        return tasks

    async def execute_pipeline(self, tasks: list[dict], context: dict) -> dict:
        """Execute agents in sequence, passing context through each."""
        for task in tasks:
            agent_name = task["agent"]
            try:
                agent = self._get_agent(agent_name)
                context = await agent.execute(context)
            except Exception as e:
                context.setdefault("errors", []).append(f"{agent_name}: {str(e)}")
                self.add_step(context, "error", f"{agent_name} 执行失败: {str(e)}")
        return context
