"""MemoryCompressor — summarizes historical memory into compact snapshots.

Compresses conversation and analysis history into key-fact summaries.
Original memory is preserved — compression is additive.
"""
from __future__ import annotations
from datetime import datetime
from database import SessionLocal
from memory.compressed_memory import CompressedMemory
from memory.memory_manager import get_memory_manager


class MemoryCompressor:
    """Compresses conversation and analysis memory into summaries."""

    def compress(self, user_id: int) -> dict:
        """Run compression for all memory types. Returns summary stats."""
        mgr = get_memory_manager()
        results = {}

        # ── Compress conversations ──
        convos = mgr.get_conversation_history(user_id, "", limit=100)
        if convos:
            summary = self._compress_conversations(convos)
            self._store(user_id, "conversation", summary,
                        len(convos), max(1, len(convos) // 10))
            results["conversation"] = {"item_count": len(convos), "summary_len": len(summary)}

        # ── Compress analyses ──
        analyses = mgr.get_recent_analyses(user_id, limit=100)
        if analyses:
            summary = self._compress_analyses(analyses)
            self._store(user_id, "analysis", summary,
                        len(analyses), max(1, len(analyses) // 5))
            results["analysis"] = {"item_count": len(analyses), "summary_len": len(summary)}

        return results

    def get_compressed(self, user_id: int) -> list[dict]:
        """Get compressed memory entries for a user."""
        db = SessionLocal()
        try:
            rows = db.query(CompressedMemory).filter(
                CompressedMemory.user_id == user_id
            ).order_by(CompressedMemory.id.desc()).all()
            return [{
                "id": r.id, "memory_type": r.memory_type,
                "summary": r.summary, "item_count": r.item_count,
                "compressed_count": r.compressed_count,
                "created_at": r.created_at,
            } for r in rows]
        finally:
            db.close()

    def _store(self, user_id: int, memory_type: str, summary: str,
               item_count: int, compressed_count: int) -> None:
        db = SessionLocal()
        try:
            db.add(CompressedMemory(
                user_id=user_id,
                memory_type=memory_type,
                summary=summary[:2000],
                item_count=item_count,
                compressed_count=compressed_count,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def _compress_conversations(self, convos: list[dict]) -> str:
        """Extract key topics from conversation history."""
        topics = []
        for c in convos[:50]:
            content = c.get("content", "")[:100]
            if content:
                topics.append(content)
        if not topics:
            return "No conversations to summarize."
        return " | ".join(topics[:8])

    def _compress_analyses(self, analyses: list[dict]) -> str:
        """Extract key findings from analysis history."""
        findings = []
        for a in analyses[:20]:
            filename = a.get("filename", "unknown")
            kpi = a.get("kpi", {})
            kpi_str = str(kpi)[:80] if kpi else ""
            findings.append(f"File: {filename} — {kpi_str}")
        if not findings:
            return "No analyses to summarize."
        return ";\n".join(findings[:8])
