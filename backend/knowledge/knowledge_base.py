"""KnowledgeBase — loads JSON knowledge documents for agent context enhancement."""
from __future__ import annotations
import os
import json


class KnowledgeBase:
    """In-memory knowledge store loaded from JSON files."""

    def __init__(self, documents_dir: str | None = None):
        self._entries: list[dict] = []
        self._categories: set[str] = set()
        if documents_dir is None:
            documents_dir = os.path.join(os.path.dirname(__file__), "documents")
        self._load(documents_dir)

    def _load(self, documents_dir: str) -> None:
        if not os.path.isdir(documents_dir):
            return
        for fname in sorted(os.listdir(documents_dir)):
            if fname.endswith(".json"):
                path = os.path.join(documents_dir, fname)
                try:
                    with open(path, encoding="utf-8") as f:
                        entries = json.load(f)
                        for e in entries:
                            e.setdefault("source_file", fname)
                            self._categories.add(e.get("category", "general"))
                        self._entries.extend(entries)
                except Exception as e:
                    print(f"[KnowledgeBase] error loading {fname}: {e}")
        print(f"[KnowledgeBase] loaded {len(self._entries)} entries in "
              f"{len(self._categories)} categories")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Keyword-based search. Returns top_k matching entries sorted by relevance."""
        if not query:
            return self._entries[:top_k]

        q = query.lower()
        scored = []
        for e in self._entries:
            score = 0
            # Keyword match in title
            title = e.get("title", "").lower()
            if q in title:
                score += 3
            # Keyword match in content
            content = e.get("content", "").lower()
            if q in content:
                score += 2
            # Match individual keywords
            for kw in e.get("keywords", []):
                if kw.lower() in q:
                    score += 2
                if q in kw.lower():
                    score += 1
            if score > 0:
                scored.append((score, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def get_categories(self) -> list[str]:
        return sorted(self._categories)

    @property
    def entry_count(self) -> int:
        return len(self._entries)


# ── Singleton ─────────────────────────────────────────────

knowledge_base = KnowledgeBase()
