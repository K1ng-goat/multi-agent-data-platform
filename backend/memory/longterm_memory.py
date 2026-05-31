"""Long-term Analysis Memory — historical KPI, trend, anomaly, and report storage."""
from __future__ import annotations
import json
import logging
import traceback
from datetime import datetime
from database import SessionLocal
from memory.analysis_memory_model import AnalysisMemory

logger = logging.getLogger(__name__)


def save_analysis(user_id: int, session_id: str, filename: str,
                  analysis: dict, charts: list, report: str | None = None) -> None:
    """Save an analysis result as long-term memory."""
    print(f"[Memory LT] save_analysis — user={user_id} session={session_id} file={filename}")
    db = SessionLocal()
    try:
        kpi = _extract_kpi(analysis, charts)
        trend_json_str = json.dumps(
            {"trend": (analysis.get("trend", "") or "")[:500]}, ensure_ascii=False
        ) if isinstance(analysis, dict) else "{}"
        anomaly_json_str = json.dumps(
            {"anomaly": (analysis.get("anomaly", "") or "")[:500]}, ensure_ascii=False
        ) if isinstance(analysis, dict) else "{}"

        db.add(AnalysisMemory(
            user_id=user_id,
            session_id=session_id,
            filename=filename or "",
            kpi_json=json.dumps(kpi, ensure_ascii=False),
            trend_json=trend_json_str,
            anomaly_json=anomaly_json_str,
            report_content=(report or "")[:5000],
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        print("[Memory LT] committing...")
        db.commit()
        print("[Memory LT] commit OK")
    except Exception:
        print("[Memory LT] ERROR on save_analysis:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            logger.exception("[Memory LT] ERROR during rollback")
    finally:
        db.close()


def get_recent_analyses(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent analysis memories for a user."""
    print(f"[Memory LT] get_recent_analyses — user={user_id}")
    db = SessionLocal()
    try:
        rows = db.query(AnalysisMemory).filter(
            AnalysisMemory.user_id == user_id,
        ).order_by(AnalysisMemory.id.desc()).limit(limit).all()
        print(f"[Memory LT] get_recent_analyses — found {len(rows)} rows")
        return [_row_to_dict(r) for r in rows]
    except Exception:
        print("[Memory LT] ERROR on get_recent_analyses:")
        traceback.print_exc()
        return []
    finally:
        db.close()


def get_analysis(user_id: int, session_id: str) -> dict | None:
    """Get a specific analysis memory."""
    print(f"[Memory LT] get_analysis — user={user_id} session={session_id}")
    db = SessionLocal()
    try:
        row = db.query(AnalysisMemory).filter(
            AnalysisMemory.user_id == user_id,
            AnalysisMemory.session_id == session_id,
        ).first()
        return _row_to_dict(row) if row else None
    except Exception:
        print("[Memory LT] ERROR on get_analysis:")
        traceback.print_exc()
        return None
    finally:
        db.close()


def search_similar_analyses(user_id: int, keyword: str, limit: int = 5) -> list[dict]:
    """Search analysis memories by keyword in filename or report content."""
    print(f"[Memory LT] search_similar_analyses — user={user_id} keyword={keyword[:30]}")
    db = SessionLocal()
    try:
        rows = db.query(AnalysisMemory).filter(
            AnalysisMemory.user_id == user_id,
            (AnalysisMemory.filename.contains(keyword)) |
            (AnalysisMemory.report_content.contains(keyword)),
        ).order_by(AnalysisMemory.id.desc()).limit(limit).all()
        print(f"[Memory LT] search_similar_analyses — found {len(rows)} rows")
        return [_row_to_dict(r) for r in rows]
    except Exception:
        print("[Memory LT] ERROR on search_similar_analyses:")
        traceback.print_exc()
        return []
    finally:
        db.close()


def clear_analyses(user_id: int) -> int:
    """Delete all analysis memories for a user. Returns count deleted."""
    print(f"[Memory LT] clear_analyses — user={user_id}")
    db = SessionLocal()
    try:
        count = db.query(AnalysisMemory).filter(
            AnalysisMemory.user_id == user_id,
        ).delete()
        db.commit()
        print(f"[Memory LT] clear_analyses — deleted {count} rows")
        return count
    except Exception:
        print("[Memory LT] ERROR on clear_analyses:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            logger.exception("[Memory LT] ERROR during rollback")
        return 0
    finally:
        db.close()


def _extract_kpi(analysis: dict, charts: list) -> dict:
    """Extract KPI metadata from analysis and charts."""
    sections = list(analysis.keys()) if isinstance(analysis, dict) else []
    chart_count = len(charts) if isinstance(charts, list) else 0
    chart_types = [c.get("type") for c in charts if isinstance(c, dict)] if isinstance(charts, list) else []
    return {
        "analysis_sections": sections,
        "chart_count": chart_count,
        "chart_types": chart_types,
    }


def _row_to_dict(row: AnalysisMemory) -> dict:
    kpi = {}
    trend = {}
    anomaly = {}
    try:
        if row.kpi_json:
            kpi = json.loads(row.kpi_json)
    except Exception:
        print(f"[Memory LT] ERROR parsing kpi_json for id={row.id}")
    try:
        if row.trend_json:
            trend = json.loads(row.trend_json)
    except Exception:
        print(f"[Memory LT] ERROR parsing trend_json for id={row.id}")
    try:
        if row.anomaly_json:
            anomaly = json.loads(row.anomaly_json)
    except Exception:
        print(f"[Memory LT] ERROR parsing anomaly_json for id={row.id}")
    return {
        "id": row.id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "filename": row.filename,
        "kpi": kpi,
        "trend": trend,
        "anomaly": anomaly,
        "report": row.report_content,
        "created_at": row.created_at,
    }
