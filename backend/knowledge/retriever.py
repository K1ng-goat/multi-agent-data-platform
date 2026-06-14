"""Retriever — knowledge retrieval layer for agent RAG.

Wraps KnowledgeBase.search() with scoring, metrics tracking, and
prompt-context formatting for agent consumption.
"""
from __future__ import annotations
import json
import threading
from .knowledge_base import knowledge_base
from cache_manager import cache  # T44 Redis cache


class RetrieverService:
    """Semantic retrieval service for agent knowledge injection."""

    def __init__(self):
        self._count: int = 0
        self._hits: int = 0
        self._category_hits: dict[str, int] = {}
        self._lock = threading.Lock()

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search knowledge base with cache layer."""
        ck = cache.make_key("knowledge", query, str(top_k))
        cached = cache.get(ck)
        if cached:
            return json.loads(cached)

        results = knowledge_base.search(query, top_k)
        cache.set(ck, json.dumps(results, ensure_ascii=False, default=str), ttl=3600)
        with self._lock:
            self._count += 1
            if results:
                self._hits += 1
                for r in results:
                    cat = r.get("category", "unknown")
                    self._category_hits[cat] = self._category_hits.get(cat, 0) + 1
        return [
            {"title": r["title"], "category": r["category"],
             "content": r["content"], "score": len(r.get("keywords", []))}
            for r in results
        ]

    def retrieve_for_prompt(self, query: str, top_k: int = 3) -> str:
        """Retrieve knowledge and format as prompt context."""
        results = self.search(query, top_k)
        if not results:
            return ""
        lines = ["[Knowledge Context]"]
        for r in results:
            lines.append(f"- {r['title']}: {r['content'][:150]}")
        return "\n".join(lines) + "\n\n"

    def get_stats(self) -> dict:
        with self._lock:
            hit_rate = round(self._hits / self._count * 100, 1) if self._count > 0 else 0
            return {
                "retrieval_count": self._count,
                "hit_count": self._hits,
                "hit_rate": hit_rate,
                "top_categories": sorted(self._category_hits.items(), key=lambda x: x[1], reverse=True)[:5],
            }

    def reset(self) -> None:
        with self._lock:
            self._count = 0
            self._hits = 0
            self._category_hits.clear()


# ── Singleton ─────────────────────────────────────────────

retriever = RetrieverService()
