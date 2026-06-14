"""CacheManager — Redis-backed cache with in-memory fallback.

Uses Redis when REDIS_URL is set and ENABLE_REDIS_CACHE=true.
Falls back to in-memory dict if Redis is unavailable.
Exposes hit/miss metrics via GET /cache/stats.
"""
from __future__ import annotations
import os
import json
import time
import hashlib
import threading

# Try to import redis — gracefully fail if not installed
try:
    import redis as _redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False


class CacheManager:
    """Hybrid cache: Redis first, in-memory fallback."""

    def __init__(self):
        self._redis = None
        self._fallback: dict[str, tuple[str, float | None]] = {}  # value, expiry
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._enabled = os.getenv("ENABLE_REDIS_CACHE", "false").lower() in ("true", "1", "yes")
        self._connect()

    def _connect(self) -> None:
        if not self._enabled or not _HAS_REDIS:
            return
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self._redis = _redis.from_url(url, socket_connect_timeout=2)
            self._redis.ping()
            print(f"[CacheManager] Redis connected: {url}")
        except Exception as e:
            print(f"[CacheManager] Redis unavailable ({e}), using in-memory fallback")
            self._redis = None

    def get(self, key: str) -> str | None:
        """Get a cached value. Returns None on miss."""
        val = None
        # Try Redis
        if self._redis:
            try:
                raw = self._redis.get(key)
                if raw:
                    val = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            except Exception:
                pass
        # Fallback: in-memory
        if val is None:
            with self._lock:
                entry = self._fallback.get(key)
                if entry:
                    data, expiry = entry
                    if expiry is None or time.time() < expiry:
                        val = data
                    else:
                        del self._fallback[key]

        if val is not None:
            self._hits += 1
            return val
        self._misses += 1
        return None

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set a cached value with optional TTL (seconds)."""
        # Try Redis
        if self._redis:
            try:
                if ttl:
                    self._redis.setex(key, ttl, value)
                else:
                    self._redis.set(key, value)
                return
            except Exception:
                pass
        # Fallback
        with self._lock:
            expiry = time.time() + ttl if ttl else None
            self._fallback[key] = (value, expiry)
            if len(self._fallback) > 1000:
                oldest = next(iter(self._fallback))
                del self._fallback[oldest]

    def delete(self, key: str) -> None:
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass
        with self._lock:
            self._fallback.pop(key, None)

    def clear(self) -> None:
        if self._redis:
            try:
                self._redis.flushdb()
            except Exception:
                pass
        with self._lock:
            self._fallback.clear()

    def get_stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            "backend": "redis" if self._redis else "memory",
            "enabled": self._enabled,
        }

    @staticmethod
    def make_key(prefix: str, *args: str) -> str:
        """Create a deterministic cache key from prefix + args."""
        raw = prefix + ":" + "|".join(args)
        return prefix + ":" + hashlib.md5(raw.encode()).hexdigest()[:16]


# ── Singleton ─────────────────────────────────────────────

cache = CacheManager()
