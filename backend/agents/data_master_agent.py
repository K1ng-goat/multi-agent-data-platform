"""Master Agent — intent classification, task planning, agent routing, pipeline execution."""
from .base_agent import BaseAgent
from .data_agent import DataAgent
from .chart_agent import ChartAgent
from .audit_agent import AuditAgent
from .report_agent import ReportAgent
from .style_agent import StyleAgent
from .export_agent import ExportAgent
from intent_classifier import classify as _classify

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

        # Step 1: Classify intent (T6: unified single-source-of-truth)
        intent = _classify(user_message)
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
