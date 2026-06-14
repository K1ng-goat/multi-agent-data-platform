"""ChatPlannerAgent — determines execution plan for /chat endpoint.

Maps user messages to agents and tools via the intent classifier,
replacing the old hard-coded tool dispatch path.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from intent_classifier import classify_for_chat


@dataclass
class ChatExecutionPlan:
    intent: str = "chat"
    mode: str = "chat"              # "chat" | "workflow" | "agent"
    required_agents: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    needs_memory: bool = True
    needs_style_detection: bool = False

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "mode": self.mode,
            "required_agents": self.required_agents,
            "required_tools": self.required_tools,
            "needs_memory": self.needs_memory,
        }


class ChatPlannerAgent:
    name = "ChatPlannerAgent"
    description = "Chat Planner — maps user messages to agent execution plans"

    def plan(self, user_message: str, session: dict | None = None) -> ChatExecutionPlan:
        intent = classify_for_chat(user_message)

        if intent == "workflow":
            return ChatExecutionPlan(
                intent="analyze_and_report",
                mode="workflow",
                required_agents=["DataAgent", "ReportAgent"],
                required_tools=["ExcelTool", "MemoryTool"],
                needs_style_detection=True,
            )

        return ChatExecutionPlan(
            intent="chat",
            mode="chat",
            required_agents=["DataAgent"],
            required_tools=["ExcelTool"],
        )
