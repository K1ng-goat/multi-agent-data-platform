"""PluginLoader — auto-discovers and registers agent plugins.

Scans agents/ and agents/plugins/ directories for BaseAgent subclasses.
Automatically registers them with the AgentRegistry at startup.
"""
from __future__ import annotations
import os
import importlib
import pkgutil
from .base_agent import BaseAgent


class PluginLoader:
    """Auto-discovers agent classes and registers them."""

    def __init__(self, registry):
        self._registry = registry
        self._loaded: list[str] = []

    def load_plugins(self) -> int:
        """Scan for and register all BaseAgent subclasses. Returns count loaded."""
        count = 0

        # Scan agents/ package
        agents_dir = os.path.dirname(__file__)
        for _, module_name, is_pkg in pkgutil.iter_modules([agents_dir]):
            if module_name.startswith('_') or module_name == 'base_agent':
                continue
            try:
                mod = importlib.import_module(f'.{module_name}', package='agents')
                count += self._register_from_module(mod)
            except Exception as e:
                print(f"[PluginLoader] skip {module_name}: {e}")

        # Scan agents/plugins/ directory
        plugins_dir = os.path.join(agents_dir, 'plugins')
        if os.path.isdir(plugins_dir):
            for _, module_name, _ in pkgutil.iter_modules([plugins_dir]):
                try:
                    mod = importlib.import_module(f'.plugins.{module_name}', package='agents')
                    count += self._register_from_module(mod)
                except Exception as e:
                    print(f"[PluginLoader] skip plugin {module_name}: {e}")

        print(f"[PluginLoader] loaded {count} agent(s)")
        return count

    def _register_from_module(self, module) -> int:
        count = 0
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                    issubclass(attr, BaseAgent) and
                    attr is not BaseAgent and
                    hasattr(attr, 'name') and
                    attr.name != 'base'):
                # Check if already registered (avoid duplicate)
                if attr.name not in self._registry.list_agents():
                    self._registry.register(attr.name, attr)
                    self._loaded.append(attr.name)
                    count += 1
        return count

    @property
    def loaded_agents(self) -> list[str]:
        return self._loaded


def auto_load(registry) -> PluginLoader:
    """Convenience: create and run a PluginLoader for the given registry."""
    loader = PluginLoader(registry)
    loader.load_plugins()
    return loader
