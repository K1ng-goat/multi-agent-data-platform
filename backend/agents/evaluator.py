"""AgentEvaluator — heuristic output quality scoring for agent results.

Scores each agent output on 4 dimensions: completeness, consistency,
readability, relevance.  Results are aggregated per agent.
"""
from __future__ import annotations
import threading
from dataclasses import dataclass, field


@dataclass
class EvaluationResult:
    agent_name: str = ""
    completeness: float = 0.0     # 0-100
    consistency: float = 0.0      # 0-100
    readability: float = 0.0     # 0-100
    relevance: float = 0.0       # 0-100

    @property
    def final_score(self) -> float:
        return round(
            (self.completeness + self.consistency +
             self.readability + self.relevance) / 4, 1
        )

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "completeness": self.completeness,
            "consistency": self.consistency,
            "readability": self.readability,
            "relevance": self.relevance,
            "final_score": self.final_score,
        }


class AgentEvaluator:
    """Heuristic evaluator for agent output quality."""

    def __init__(self):
        self._results: dict[str, list[EvaluationResult]] = {}
        self._lock = threading.Lock()

    def evaluate(self, agent_name: str, output: dict | None = None,
                 context: dict | None = None) -> EvaluationResult:
        """Score agent output heuristically."""
        result = EvaluationResult(agent_name=agent_name)

        if output is None:
            output = {}
        if context is None:
            context = {}

        # ── Completeness: did the agent produce non-empty output? ──
        non_empty = sum(1 for v in output.values() if v)
        total = max(len(output), 1)
        result.completeness = min(100, round(non_empty / total * 100, 1))

        # ── Consistency: is the output dict well-structured? ──
        str_keys = sum(1 for k in output if isinstance(k, str))
        result.consistency = min(100, round(str_keys / max(total, 1) * 100, 1))

        # ── Readability: are string values reasonably sized? ──
        str_vals = [v for v in output.values() if isinstance(v, str)]
        if str_vals:
            avg_len = sum(len(v) for v in str_vals) / len(str_vals)
            result.readability = min(100, max(60, round(avg_len / 5, 1)))
        else:
            result.readability = 70.0

        # ── Relevance: does the output relate to the context intent? ──
        intent = context.get("intent", "")
        if intent and any(intent in str(v).lower() for v in output.values() if isinstance(v, str)):
            result.relevance = 85.0
        else:
            result.relevance = 60.0

        # ── Store ──
        with self._lock:
            if agent_name not in self._results:
                self._results[agent_name] = []
            self._results[agent_name].append(result)

        return result

    def get_agent_stats(self, agent_name: str) -> dict | None:
        with self._lock:
            results = self._results.get(agent_name, [])
            if not results:
                return None
            scores = [r.final_score for r in results]
            return {
                "agent_name": agent_name,
                "runs": len(results),
                "avg_score": round(sum(scores) / len(scores), 1),
                "min_score": min(scores),
                "max_score": max(scores),
            }

    def get_all_stats(self) -> dict[str, dict]:
        with self._lock:
            return {name: self.get_agent_stats(name)
                    for name in self._results
                    if self.get_agent_stats(name) is not None}

    def reset(self) -> None:
        with self._lock:
            self._results.clear()


# ── Singleton ─────────────────────────────────────────────

evaluator = AgentEvaluator()
