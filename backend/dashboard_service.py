"""Dashboard data aggregation — persists via SQLite."""
from __future__ import annotations
import json
import traceback
from datetime import datetime
import pandas as pd
from database import SessionLocal
from dashboard_model import DashboardSnapshot
import reports_service as rs


def update_snapshot(session_id: str, data_summary: dict, analysis: dict, charts: list[dict], user_id: int = 0):
    """Store a snapshot after each /analyze call."""
    rs.save_report(session_id, data_summary, analysis, charts, user_id)

    db = SessionLocal()
    try:
        kpi = _extract_kpi(data_summary)
        chart_data = _summarize_charts(charts)
        now = datetime.now().isoformat()

        existing = db.query(DashboardSnapshot).filter(
            DashboardSnapshot.session_id == session_id,
            DashboardSnapshot.user_id == user_id,
        ).first()

        if existing:
            existing.filename = data_summary.get("filename", "")
            existing.rows = data_summary.get("shape", {}).get("rows", 0)
            existing.columns = data_summary.get("shape", {}).get("columns", 0)
            existing.kpi = json.dumps(kpi, ensure_ascii=False)
            existing.charts = json.dumps(chart_data, ensure_ascii=False)
            existing.ai_summary = analysis.get("summary", "")
            existing.ai_trend = analysis.get("trend", "")
            existing.ai_anomaly = analysis.get("anomaly", "")
            existing.columns_list = json.dumps(data_summary.get("columns", []), ensure_ascii=False)
            existing.updated_at = now
        else:
            snap = DashboardSnapshot(
                session_id=session_id,
                user_id=user_id,
                filename=data_summary.get("filename", ""),
                rows=data_summary.get("shape", {}).get("rows", 0),
                columns=data_summary.get("shape", {}).get("columns", 0),
                kpi=json.dumps(kpi, ensure_ascii=False),
                charts=json.dumps(chart_data, ensure_ascii=False),
                ai_summary=analysis.get("summary", ""),
                ai_trend=analysis.get("trend", ""),
                ai_anomaly=analysis.get("anomaly", ""),
                columns_list=json.dumps(data_summary.get("columns", []), ensure_ascii=False),
                updated_at=now,
            )
            db.add(snap)
        db.commit()
        print("[dashboard_service] DB commit OK — session_id:", session_id)
    except Exception:
        print("[dashboard_service] ERROR on DB commit:")
        traceback.print_exc()
    finally:
        db.close()


def get_dashboard(user_id: int = 0) -> dict:
    """Return the dashboard data for the frontend, scoped to user."""
    db = SessionLocal()
    try:
        snap = db.query(DashboardSnapshot).filter(
            DashboardSnapshot.user_id == user_id
        ).order_by(DashboardSnapshot.id.desc()).first()
    finally:
        db.close()

    if not snap:
        return {
            "has_data": False,
            "kpi": [],
            "charts": [],
            "ai_summary": "",
            "recent_files": [],
        }

    kpi = [
        {"label": "数据行数", "value": f"{snap.rows:,}", "icon": "rows", "change": ""},
        {"label": "数据列数", "value": str(snap.columns), "icon": "columns", "change": ""},
        {"label": "检测异常", "value": "已分析" if snap.ai_anomaly else "无异常", "icon": "anomaly", "change": ""},
        {"label": "AI 建议", "value": "已生成" if snap.ai_trend else "待分析", "icon": "ai", "change": ""},
    ]

    return {
        "has_data": True,
        "filename": snap.filename or "",
        "session_id": snap.session_id or "",
        "updated_at": snap.updated_at or "",
        "kpi": kpi,
        "charts": _safe_json_loads(snap.charts, []),
        "ai_summary": snap.ai_summary or "",
        "ai_trend": snap.ai_trend or "",
        "ai_anomaly": snap.ai_anomaly or "",
        "columns_list": _safe_json_loads(snap.columns_list, []),
    }


def _safe_json_loads(val: str, default):
    """Safely parse JSON, returning default on failure."""
    try:
        return json.loads(val) if val else default
    except (json.JSONDecodeError, TypeError):
        return default


def _summarize_charts(charts: list[dict]) -> list[dict]:
    """Pass through chart configs, keeping only what the dashboard needs."""
    result = []
    for c in charts:
        result.append({
            "type": c.get("type", "line"),
            "title": c.get("title", ""),
            "labels": c.get("labels", [])[:20],
            "datasets": [
                {"name": ds.get("name", ""), "data": ds.get("data", [])[:20]}
                for ds in c.get("datasets", [])
            ],
        })
    return result


def _extract_kpi(data_summary: dict) -> dict:
    """Extract key numbers from data summary for KPI cards."""
    describe = data_summary.get("describe", {})
    kpi = {}

    def _is_numeric(val) -> bool:
        """Check if a value is numeric or a numeric string."""
        if val is None:
            return False
        if isinstance(val, (int, float)):
            return not (isinstance(val, float) and pd.isna(val))
        if isinstance(val, str):
            if not val or val.strip() == "":
                return False
            try:
                float(val)
                return True
            except (ValueError, TypeError):
                return False
        return False

    def _safe_round(val) -> float:
        """Safely round a value to 2 decimal places, handling non-numeric types."""
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return 0.0
            return round(float(val), 2)
        if isinstance(val, str):
            if not val or val.strip() == "":
                return 0.0
            try:
                return round(float(val), 2)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    for col, vals in describe.items():
        if not isinstance(vals, dict):
            continue
        if "mean" not in vals:
            continue
        mean_val = vals.get("mean", 0)
        max_val = vals.get("max", 0)
        sum_val = vals.get("sum", 0)
        if not any(_is_numeric(v) for v in [mean_val, max_val, sum_val]):
            continue
        kpi[col] = {
            "mean": _safe_round(mean_val),
            "max": _safe_round(max_val),
            "sum": _safe_round(sum_val),
        }
    return kpi
