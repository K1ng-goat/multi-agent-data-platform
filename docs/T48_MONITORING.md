# T48 Monitoring & Observability

> **Date**: 2026-06-04

---

## Endpoints

```
GET /system/metrics     → CPU, memory, disk, uptime
GET /system/stats       → request counts (total, analyze, chat, errors)
GET /system/performance → API latency averages
GET /system/dashboard   → all aggregated (system + requests + perf + db + cache + agents)
```

## System Dashboard

```json
{
  "system":      {"cpu_percent": -1, "memory_percent": -1, "uptime_seconds": 0},
  "requests":    {"total_requests": 0, "analyze_requests": 0, "error_count": 0},
  "performance": {"analyze_avg_ms": 0, "chat_avg_ms": 0},
  "database":    {"database_type": "sqlite", "tables": 11},
  "cache":       {"hits": 2, "misses": 1, "hit_rate": 66.7},
  "agents":      {"DataAgent": {"runs": 3, "success_rate": 100}}
}
```

## Graceful Fallback

```
psutil not installed → cpu/memory = -1
Any error → fallback with note field
```

## Files

| File | Change |
|------|--------|
| `system_monitor.py` | **NEW** — RequestStats, LatencyTracker, get_system_metrics (90 lines) |
| `main.py` | **MODIFIED** — +4 endpoints |
| `docs/T48_MONITORING.md` | Design document |

## Verification

```
/system/metrics:     200 (cpu=-1, graceful psutil fallback)
/system/stats:       200 (request counters)
/system/performance: 200 (latency averages)
/system/dashboard:   200 (6 keys aggregated)
Routes:              65
```