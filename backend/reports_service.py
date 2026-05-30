"""Reports storage — persists analysis history via SQLite."""
from __future__ import annotations
import json
import traceback
from datetime import datetime
from database import SessionLocal
from report_model import Report


def save_report(session_id: str, data_summary: dict, analysis: dict, charts: list[dict], user_id: int = 0):
    """Save an analysis snapshot to the database."""
    db = SessionLocal()
    try:
        report = Report(
            session_id=session_id,
            user_id=user_id,
            filename=data_summary.get("filename", ""),
            rows=data_summary.get("shape", {}).get("rows", 0),
            columns=data_summary.get("shape", {}).get("columns", 0),
            columns_list=json.dumps(data_summary.get("columns", []), ensure_ascii=False),
            summary=analysis.get("summary", ""),
            anomaly=analysis.get("anomaly", ""),
            trend=analysis.get("trend", ""),
            charts=json.dumps(_summarize_charts(charts), ensure_ascii=False),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        db.add(report)
        db.commit()
        print("[reports_service] DB commit OK — session_id:", session_id)
    except Exception:
        print("[reports_service] ERROR on DB commit:")
        traceback.print_exc()
    finally:
        db.close()


def get_reports(user_id: int = 0) -> list[dict]:
    """Return all reports for a user, newest first."""
    db = SessionLocal()
    try:
        rows = db.query(Report).filter(Report.user_id == user_id).order_by(Report.id.desc()).all()
        return [_report_to_dict(r) for r in rows]
    finally:
        db.close()


def get_report(report_id: str, user_id: int = 0) -> dict | None:
    """Return a single report by session_id, scoped to user."""
    db = SessionLocal()
    try:
        row = db.query(Report).filter(
            Report.session_id == report_id,
            Report.user_id == user_id,
        ).first()
        return _report_to_dict(row) if row else None
    finally:
        db.close()


def _report_to_dict(r: Report) -> dict:
    """Convert ORM object to dict, deserializing JSON fields."""
    return {
        "id": r.session_id,
        "filename": r.filename,
        "rows": r.rows,
        "columns": r.columns,
        "columns_list": _safe_json_loads(r.columns_list, []),
        "summary": r.summary or "",
        "anomaly": r.anomaly or "",
        "trend": r.trend or "",
        "charts": _safe_json_loads(r.charts, []),
        "created_at": r.created_at or "",
        "created_at_iso": r.created_at or "",
    }


def _safe_json_loads(val: str, default):
    """Safely parse JSON, returning default on failure."""
    try:
        return json.loads(val) if val else default
    except (json.JSONDecodeError, TypeError):
        return default


def _summarize_charts(charts: list[dict]) -> list[dict]:
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
