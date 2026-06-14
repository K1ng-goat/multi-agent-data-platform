"""SystemMonitor — production-grade metrics and observability.

Tracks CPU, memory, request counts, and API latency.
Graceful fallback if psutil is unavailable.
"""
from __future__ import annotations
import os
import time
import threading

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

_START_TIME = time.time()


class RequestStats:
    def __init__(self):
        self._total = 0
        self._analyze = 0
        self._chat = 0
        self._agent_chat = 0
        self._errors = 0
        self._lock = threading.Lock()

    def record(self, endpoint: str, is_error: bool = False) -> None:
        with self._lock:
            self._total += 1
            if "analyze" in endpoint:
                self._analyze += 1
            elif "chat" in endpoint and "agent" not in endpoint:
                self._chat += 1
            elif "agent-chat" in endpoint:
                self._agent_chat += 1
            if is_error:
                self._errors += 1

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_requests": self._total,
                "analyze_requests": self._analyze,
                "chat_requests": self._chat,
                "agent_chat_requests": self._agent_chat,
                "error_count": self._errors,
                "uptime_seconds": round(time.time() - _START_TIME, 1),
            }


class LatencyTracker:
    def __init__(self):
        self._analyze_times: list[float] = []
        self._chat_times: list[float] = []
        self._agent_chat_times: list[float] = []
        self._lock = threading.Lock()

    def record(self, endpoint: str, duration_ms: float) -> None:
        with self._lock:
            if "analyze" in endpoint and "agent" not in endpoint:
                self._analyze_times.append(duration_ms)
            elif "chat" in endpoint and "agent" not in endpoint:
                self._chat_times.append(duration_ms)
            elif "agent-chat" in endpoint:
                self._agent_chat_times.append(duration_ms)

    def get_performance(self) -> dict:
        def avg(lst): return round(sum(lst[-50:]) / len(lst[-50:]), 1) if lst else 0
        with self._lock:
            return {
                "analyze_avg_ms": avg(self._analyze_times),
                "chat_avg_ms": avg(self._chat_times),
                "agent_chat_avg_ms": avg(self._agent_chat_times),
            }


def get_system_metrics() -> dict:
    if _HAS_PSUTIL:
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "uptime_seconds": round(time.time() - _START_TIME, 1),
            }
        except Exception:
            pass
    return {
        "cpu_percent": -1,
        "memory_percent": -1,
        "disk_percent": -1,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "note": "psutil not installed",
    }


def get_full_dashboard(
    cache_stats_fn=None,
    db_info_fn=None,
    agent_metrics_fn=None,
) -> dict:
    return {
        "system": get_system_metrics(),
        "requests": request_stats.get_stats(),
        "performance": latency_tracker.get_performance(),
        "database": db_info_fn() if db_info_fn else {},
        "cache": cache_stats_fn() if cache_stats_fn else {},
        "agents": agent_metrics_fn() if agent_metrics_fn else {},
    }


# ── Singletons ────────────────────────────────────────────

request_stats = RequestStats()
latency_tracker = LatencyTracker()
