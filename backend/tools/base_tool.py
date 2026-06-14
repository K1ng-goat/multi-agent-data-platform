"""BaseTool — abstract interface for all tools."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """All tools inherit from this.  Tools are stateless callable objects
    that perform a specific task (parse, chart, export, etc.).
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """Execute the tool and return a result dict."""
        ...
