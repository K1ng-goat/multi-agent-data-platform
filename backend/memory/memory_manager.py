"""MemoryManager — central orchestrator for all 4 memory layers.

Provides:
- retrieve_relevant_memories(): inject relevant context before agent execution
- save_*(): persist memories after execution
- summarization: compress old memories
"""
from __future__ import annotations
import json
import logging
import traceback
from memory import user_memory as um
from memory import workspace_memory as wm
from memory import conversation_memory as cm
from memory import longterm_memory as lm

logger = logging.getLogger(__name__)


class MemoryManager:
    """Central memory orchestrator used by the Agent pipeline."""

    # ── Retrieval ─────────────────────────────────────────

    def retrieve_relevant_memories(self, user_id: int, context: dict) -> dict:
        """Retrieve memories relevant to the current execution context."""
        print(f"[Memory Mgr] retrieve_relevant_memories — user={user_id}")
        user_message = context.get("user_message", "")
        session_id = context.get("session_id", "")

        memories: dict = {
            "user_preferences": {},
            "workspace_history": [],
            "recent_conversations": [],
            "historical_analyses": [],
        }

        try:
            memories["user_preferences"] = um.extract_preferences(user_id)
            print(f"[Memory Mgr] user_preferences loaded: {len(memories['user_preferences'])} keys")
        except Exception:
            print("[Memory Mgr] ERROR loading user_preferences:")
            traceback.print_exc()

        if session_id:
            try:
                ws = wm.get_workspace(user_id, session_id)
                if ws:
                    memories["workspace_history"] = [ws]
                    print("[Memory Mgr] workspace_history loaded")
            except Exception:
                print("[Memory Mgr] ERROR loading workspace_history:")
                traceback.print_exc()

        try:
            memories["recent_conversations"] = cm.get_recent_conversations(user_id, limit=5)
            print(f"[Memory Mgr] recent_conversations loaded: {len(memories['recent_conversations'])} msgs")
        except Exception:
            print("[Memory Mgr] ERROR loading recent_conversations:")
            traceback.print_exc()

        try:
            filename = context.get("data_summary", {}).get("filename", "")
            if filename:
                memories["historical_analyses"] = lm.search_similar_analyses(user_id, filename, limit=3)
            if not memories["historical_analyses"]:
                memories["historical_analyses"] = lm.get_recent_analyses(user_id, limit=3)
            print(f"[Memory Mgr] historical_analyses loaded: {len(memories['historical_analyses'])} records")
        except Exception:
            print("[Memory Mgr] ERROR loading historical_analyses:")
            traceback.print_exc()

        return memories

    def build_memory_prompt(self, memories: dict) -> str:
        """Build a condensed text prompt from retrieved memories for AI context injection."""
        parts = []

        prefs = memories.get("user_preferences", {})
        if prefs:
            prefs_str = ", ".join(f"{k}={v}" for k, v in list(prefs.items())[:8])
            parts.append(f"[用户偏好] {prefs_str}")

        hist = memories.get("historical_analyses", [])
        if hist:
            filenames = list({h.get("filename", "") for h in hist if h.get("filename")})
            if filenames:
                parts.append(f"[历史分析文件] {', '.join(filenames[:5])}")

        convos = memories.get("recent_conversations", [])
        if convos:
            recent = [c.get("content", "")[:60] for c in convos[:3] if c.get("content")]
            if recent:
                parts.append(f"[最近对话] {'; '.join(recent)}")

        prompt = "\n".join(parts) if parts else ""
        print(f"[Memory Mgr] build_memory_prompt — {len(prompt)} chars")
        return prompt

    # ── Persistence ───────────────────────────────────────

    def save_user_preference(self, user_id: int, category: str, key: str, value):
        """Save a user preference memory."""
        print(f"[Memory Mgr] save_user_preference — user={user_id} {category}/{key}")
        val_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        um.save_user_memory(user_id, category, key, val_str)

    def save_workspace(self, user_id: int, session_id: str, filename: str,
                       data_summary: dict, charts: list, analysis: dict,
                       active_theme: str = "business"):
        """Save workspace snapshot."""
        print(f"[Memory Mgr] save_workspace — user={user_id} session={session_id}")
        wm.save_workspace(user_id, session_id, filename, data_summary, charts, analysis, active_theme)

    def save_conversation_message(self, user_id: int, session_id: str, role: str,
                                  content: str, mode: str = "chat", steps: list | None = None):
        """Save a conversation message."""
        print(f"[Memory Mgr] save_conversation_message — user={user_id} role={role} mode={mode}")
        cm.save_message(user_id, session_id, role, content, mode, steps)

    def save_analysis_memory(self, user_id: int, session_id: str, filename: str,
                             analysis: dict, charts: list, report: str | None = None):
        """Save analysis result as long-term memory."""
        print(f"[Memory Mgr] save_analysis_memory — user={user_id} session={session_id}")
        lm.save_analysis(user_id, session_id, filename, analysis, charts, report)

    # ── Query (for frontend) ──────────────────────────────

    def get_user_preferences(self, user_id: int) -> dict:
        """Get all user preferences as a flat dict."""
        print(f"[Memory Mgr] get_user_preferences — user={user_id}")
        return um.get_user_memories(user_id, category="preference")

    def get_recent_analyses(self, user_id: int, limit: int = 10) -> list[dict]:
        """Get recent analysis memories."""
        print(f"[Memory Mgr] get_recent_analyses — user={user_id}")
        return lm.get_recent_analyses(user_id, limit)

    def get_workspaces(self, user_id: int, limit: int = 20) -> list[dict]:
        """Get recent workspace snapshots."""
        print(f"[Memory Mgr] get_workspaces — user={user_id}")
        return wm.get_workspaces(user_id, limit)

    def get_conversation_history(self, user_id: int, session_id: str, limit: int = 50) -> list[dict]:
        """Get conversation history for a session."""
        print(f"[Memory Mgr] get_conversation_history — user={user_id} session={session_id}")
        return cm.get_conversation(user_id, session_id, limit)

    def search_analyses(self, user_id: int, keyword: str, limit: int = 5) -> list[dict]:
        """Search analysis memories by keyword."""
        print(f"[Memory Mgr] search_analyses — user={user_id} keyword={keyword[:20]}")
        return lm.search_similar_analyses(user_id, keyword, limit)

    def get_memory_summary(self, user_id: int) -> dict:
        """Return aggregated memory stats for the Memory page."""
        print(f"[Memory Mgr] get_memory_summary — user={user_id}")
        try:
            analyses = lm.get_recent_analyses(user_id, limit=100)
            workspaces = wm.get_workspaces(user_id, limit=100)
            prefs = um.get_user_memories(user_id, category="preference")
            prefs_count = len(prefs)

            files = list({a.get("filename", "") for a in analyses if a.get("filename")})
            chart_types: dict[str, int] = {}
            for a in analyses:
                kpi = a.get("kpi", {})
                if isinstance(kpi, dict):
                    ct = kpi.get("chart_count", 0)
                    if ct:
                        chart_types["total"] = chart_types.get("total", 0) + int(ct)

            last_active = ""
            if analyses:
                last_active = analyses[0].get("created_at", "") or ""
            if workspaces and (not last_active or (workspaces[0].get("updated_at", "") or "") > last_active):
                last_active = workspaces[0].get("updated_at", "") or last_active

            total_conversations = 0
            try:
                convos = cm.get_recent_conversations(user_id, limit=1000)
                sessions = {c.get("session_id", "") for c in convos if c.get("session_id")}
                total_conversations = len(sessions)
            except Exception:
                logger.exception("[Memory Mgr] ERROR counting conversation sessions")

            return {
                "total_analyses": len(analyses),
                "total_workspaces": len(workspaces),
                "total_conversations": total_conversations,
                "preferences_count": prefs_count,
                "analyzed_files": files[:10],
                "chart_types": chart_types,
                "last_active": last_active,
            }
        except Exception:
            print("[Memory Mgr] ERROR on get_memory_summary:")
            traceback.print_exc()
            return {
                "total_analyses": 0, "total_workspaces": 0,
                "total_conversations": 0, "preferences_count": 0,
                "analyzed_files": [], "chart_types": {}, "last_active": "",
            }

    def clear_analyses(self, user_id: int) -> int:
        """Delete all analysis memories for a user. Returns count deleted."""
        print(f"[Memory Mgr] clear_analyses — user={user_id}")
        return lm.clear_analyses(user_id)

    def clear_workspaces(self, user_id: int) -> int:
        """Delete all workspace memories for a user. Returns count deleted."""
        print(f"[Memory Mgr] clear_workspaces — user={user_id}")
        return wm.clear_workspaces(user_id)

    def clear_preferences(self, user_id: int) -> int:
        """Delete all user preference memories. Returns count deleted."""
        print(f"[Memory Mgr] clear_preferences — user={user_id}")
        return um.clear_preferences(user_id)

    def delete_preference(self, user_id: int, key: str) -> bool:
        """Delete a single preference by key from the 'preference' category."""
        print(f"[Memory Mgr] delete_preference — user={user_id} key={key}")
        return um.delete_user_memory(user_id, "preference", key)


# Singleton
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
