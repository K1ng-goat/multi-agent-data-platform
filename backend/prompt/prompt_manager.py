"""PromptManager — centralized template loading and caching.

Loads .txt templates from prompt/templates/ at startup.
Supports format() substitution and hot-reload via POST /prompts/reload.
"""
from __future__ import annotations
import os


class PromptManager:
    """Singleton template manager for agent prompts."""

    def __init__(self, templates_dir: str | None = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self._templates_dir = templates_dir
        self._cache: dict[str, str] = {}
        self.load()

    def load(self) -> int:
        """Load all .txt templates from disk. Returns count loaded."""
        self._cache.clear()
        if not os.path.isdir(self._templates_dir):
            return 0
        for fname in sorted(os.listdir(self._templates_dir)):
            if fname.endswith(".txt"):
                name = fname[:-4]
                path = os.path.join(self._templates_dir, fname)
                with open(path, encoding="utf-8") as f:
                    self._cache[name] = f.read()
        print(f"[PromptManager] loaded {len(self._cache)} templates")
        return len(self._cache)

    def get(self, name: str, **kwargs) -> str:
        """Get a template by name, optionally with format() substitution."""
        template = self._cache.get(name, "")
        if kwargs:
            return template.format(**kwargs)
        return template

    def list_templates(self) -> list[str]:
        return sorted(self._cache.keys())

    def reload(self) -> int:
        """Hot-reload all templates from disk."""
        return self.load()

    @property
    def count(self) -> int:
        return len(self._cache)


# ── Singleton ─────────────────────────────────────────────

prompt_manager = PromptManager()
