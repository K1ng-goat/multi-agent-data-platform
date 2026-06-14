"""Master Agent — intent classification, task planning, agent routing, pipeline execution."""
from .base_agent import BaseAgent
from .recovery import safe_execute  # T26: fault tolerance
from .registry import registry     # T27: dynamic registry
from .parallel_executor import ParallelExecutionManager  # T32

# T27: Import all agents to trigger registry.register() at module load time.
# These replace the old hard-coded AGENT_CLASSES dict.
from .data_agent import DataAgent        # noqa: F401
from .chart_agent import ChartAgent      # noqa: F401
from .audit_agent import AuditAgent      # noqa: F401
from .report_agent import ReportAgent    # noqa: F401
from .style_agent import StyleAgent      # noqa: F401
from .export_agent import ExportAgent    # noqa: F401

from intent_classifier import classify as _classify


class DataMasterAgent(BaseAgent):
    name = "MasterAgent"
    description = "主控Agent — 意图分析、任务拆分、Agent调度、结果合并"

    def _get_agent(self, name: str) -> BaseAgent:
        """Lazy singleton lookup from the dynamic agent registry."""
        return registry.get(name)

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
        """Convert intent into an ordered agent task list (T27: registry-driven)."""
        agent_names = registry.get_intent_agents(intent)
        tasks = []
        for name in agent_names:
            agent = self._get_agent(name)
            tasks.append({
                "agent": name,
                "description": agent.description,
            })
        return tasks

    async def execute_pipeline(self, tasks: list[dict], context: dict) -> dict:
        """Execute agents with parallel groups + fault tolerance (T26+T32).

        Independent agents (e.g., AuditAgent + ChartAgent) run concurrently
        via asyncio.gather(). Each agent still uses safe_execute() for
        retry + timeout protection.
        """
        agent_names = [t["agent"] for t in tasks]
        executor = ParallelExecutionManager(self._get_agent)
        context, results = await executor.execute(agent_names, context)

        # Build step messages
        all_success = True
        for r in results:
            if r["success"]:
                self.add_step(context, "done",
                              f"{r['agent']} OK ({r['duration_ms']}ms)")
            else:
                all_success = False
                self.add_step(context, "error",
                              f"{r['agent']} FAIL: {r['error']}")

        context["agent_results"] = results
        context["partial_success"] = not all_success
        if not all_success:
            failed = [r["agent"] for r in results if not r["success"]]
            context.setdefault("errors", []).append(
                f"Partial success: {len(failed)} agent(s) failed — {failed}"
            )

        return context
