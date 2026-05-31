"""WorkspaceMemory service — persistent workspace state snapshots."""
from __future__ import annotations
import json
import logging
import traceback
from datetime import datetime
from database import SessionLocal
from memory.workspace_memory_model import WorkspaceMemory

logger = logging.getLogger(__name__)


def save_workspace(user_id: int, session_id: str, filename: str,
                   data_summary: dict, charts: list, analysis: dict,
                   active_theme: str = "business") -> None:
    """Save or update a workspace snapshot."""
    print(f"[Memory WS] save_workspace — user={user_id} session={session_id} file={filename}")
    db = SessionLocal()
    try:
        data_json = json.dumps(_summarize_data(data_summary), ensure_ascii=False)
        charts_json = json.dumps(_summarize_charts(charts), ensure_ascii=False)
        analysis_json = json.dumps(_summarize_analysis(analysis), ensure_ascii=False)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        row = db.query(WorkspaceMemory).filter(
            WorkspaceMemory.user_id == user_id,
            WorkspaceMemory.session_id == session_id,
        ).first()

        if row:
            print("[Memory WS] updating existing row")
            row.filename = filename
            row.data_summary = data_json
            row.charts_summary = charts_json
            row.analysis_summary = analysis_json
            row.active_theme = active_theme
            row.updated_at = now
        else:
            print("[Memory WS] inserting new row")
            db.add(WorkspaceMemory(
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                data_summary=data_json,
                charts_summary=charts_json,
                analysis_summary=analysis_json,
                active_theme=active_theme,
                created_at=now,
                updated_at=now,
            ))
        print("[Memory WS] committing...")
        db.commit()
        print("[Memory WS] commit OK")
    except Exception:
        print("[Memory WS] ERROR on save_workspace:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            logger.exception("[Memory WS] ERROR during rollback")
    finally:
        db.close()


def get_workspaces(user_id: int, limit: int = 20) -> list[dict]:
    """Get recent workspace snapshots for a user."""
    print(f"[Memory WS] get_workspaces — user={user_id}")
    db = SessionLocal()
    try:
        rows = db.query(WorkspaceMemory).filter(
            WorkspaceMemory.user_id == user_id,
        ).order_by(WorkspaceMemory.updated_at.desc()).limit(limit).all()
        print(f"[Memory WS] get_workspaces — found {len(rows)} rows")
        return [_row_to_dict(r) for r in rows]
    except Exception:
        print("[Memory WS] ERROR on get_workspaces:")
        traceback.print_exc()
        return []
    finally:
        db.close()


def get_workspace(user_id: int, session_id: str) -> dict | None:
    """Get a specific workspace snapshot."""
    print(f"[Memory WS] get_workspace — user={user_id} session={session_id}")
    db = SessionLocal()
    try:
        row = db.query(WorkspaceMemory).filter(
            WorkspaceMemory.user_id == user_id,
            WorkspaceMemory.session_id == session_id,
        ).first()
        return _row_to_dict(row) if row else None
    except Exception:
        print("[Memory WS] ERROR on get_workspace:")
        traceback.print_exc()
        return None
    finally:
        db.close()


def clear_workspaces(user_id: int) -> int:
    """Delete all workspace memories for a user. Returns count deleted."""
    print(f"[Memory WS] clear_workspaces — user={user_id}")
    db = SessionLocal()
    try:
        count = db.query(WorkspaceMemory).filter(
            WorkspaceMemory.user_id == user_id,
        ).delete()
        db.commit()
        print(f"[Memory WS] clear_workspaces — deleted {count} rows")
        return count
    except Exception:
        print("[Memory WS] ERROR on clear_workspaces:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            logger.exception("[Memory WS] ERROR during rollback")
        return 0
    finally:
        db.close()


def _summarize_data(data_summary: dict) -> dict:
    if not isinstance(data_summary, dict):
        return {}
    return {
        "shape": data_summary.get("shape", {}),
        "columns": data_summary.get("columns", [])[:20] if isinstance(data_summary.get("columns"), list) else [],
        "dtypes": data_summary.get("dtypes", {}),
        "null_counts": data_summary.get("null_counts", {}),
    }


def _summarize_charts(charts: list) -> list:
    if not isinstance(charts, list):
        return []
    return [{"type": c.get("type"), "title": c.get("title")} for c in charts if isinstance(c, dict)]


def _summarize_analysis(analysis: dict) -> dict:
    if not isinstance(analysis, dict) or not analysis:
        return {}
    return {
        "summary": (analysis.get("summary", "") or "")[:300],
        "anomaly": (analysis.get("anomaly", "") or "")[:200],
        "trend": (analysis.get("trend", "") or "")[:200],
    }


def _row_to_dict(row: WorkspaceMemory) -> dict:
    data_summary = {}
    charts_summary = []
    analysis_summary = {}
    try:
        if row.data_summary:
            data_summary = json.loads(row.data_summary)
    except Exception:
        print(f"[Memory WS] ERROR parsing data_summary for id={row.id}")
    try:
        if row.charts_summary:
            charts_summary = json.loads(row.charts_summary)
    except Exception:
        print(f"[Memory WS] ERROR parsing charts_summary for id={row.id}")
    try:
        if row.analysis_summary:
            analysis_summary = json.loads(row.analysis_summary)
    except Exception:
        print(f"[Memory WS] ERROR parsing analysis_summary for id={row.id}")
    return {
        "id": row.id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "filename": row.filename,
        "data_summary": data_summary,
        "charts_summary": charts_summary,
        "analysis_summary": analysis_summary,
        "active_theme": row.active_theme,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
