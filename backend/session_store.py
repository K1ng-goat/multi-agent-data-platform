"""SessionStore — persistent session storage.

Replaces the in-memory `sessions: dict` with a hybrid backend:
  - DataFrame  → Parquet file  (session_data/{session_id}.parquet)
  - Metadata   → SQLite  (sessions table via session_model.Session)

Phase 1: infrastructure only.  main.py still uses the old `sessions` dict.
Phase 2: swap main.py to use this store.
"""
from __future__ import annotations
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Any

import pandas as pd

from database import SessionLocal
from session_model import Session

logger = logging.getLogger(__name__)

# Directory for Parquet files — relative to backend/
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "session_data")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class SessionStore:
    """Persistent session store with Parquet + SQLite backend."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    # ── File paths ───────────────────────────────────────────

    def _parquet_path(self, session_id: str) -> str:
        return os.path.join(self.data_dir, f"{session_id}.parquet")

    # ── CRUD ─────────────────────────────────────────────────

    def save(self, session_id: str, user_id: int, session: dict[str, Any]) -> None:
        """Persist a full session (df + metadata) to disk and DB."""
        print(f"[SessionStore] save — session={session_id} user={user_id}")

        # 1. Write DataFrame to Parquet
        df = session.get("df")
        if df is not None and isinstance(df, pd.DataFrame):
            path = self._parquet_path(session_id)
            df.to_parquet(path)
            print(f"[SessionStore] parquet written: {path}")

        # 2. Upsert metadata into SQLite
        db = SessionLocal()
        try:
            row = db.query(Session).filter(
                Session.user_id == user_id,
                Session.session_id == session_id,
            ).first()

            data_summary_json = _safe_json(session.get("data_summary", {}))
            analysis_json = _safe_json(session.get("analysis", {}))
            charts_json = _safe_json(session.get("charts", []))
            history_json = _safe_json(session.get("history", []))
            style_json = _safe_json(session.get("style_overrides", {}))
            now = _now()

            if row:
                row.filename = session.get("data_summary", {}).get("filename", row.filename)
                row.data_summary_json = data_summary_json
                row.analysis_json = analysis_json
                row.charts_json = charts_json
                row.history_json = history_json
                row.active_theme = session.get("active_theme", row.active_theme)
                row.style_overrides_json = style_json
                row.last_access_at = now
            else:
                db.add(Session(
                    session_id=session_id,
                    user_id=user_id,
                    filename=session.get("data_summary", {}).get("filename", ""),
                    data_summary_json=data_summary_json,
                    analysis_json=analysis_json,
                    charts_json=charts_json,
                    history_json=history_json,
                    active_theme=session.get("active_theme", "business"),
                    style_overrides_json=style_json,
                    created_at=now,
                    last_access_at=now,
                ))
            db.commit()
            print("[SessionStore] metadata saved")
        except Exception:
            print("[SessionStore] ERROR saving metadata:")
            traceback.print_exc()
            try:
                db.rollback()
            except Exception:
                logger.exception("[SessionStore] rollback failed")
        finally:
            db.close()

    def load(self, session_id: str, user_id: int) -> dict[str, Any] | None:
        """Load a full session from disk + DB.  Returns None if not found."""
        print(f"[SessionStore] load — session={session_id} user={user_id}")
        db = SessionLocal()
        try:
            row = db.query(Session).filter(
                Session.user_id == user_id,
                Session.session_id == session_id,
            ).first()
            if not row:
                print("[SessionStore] not found")
                return None

            # Update last_access_at
            row.last_access_at = _now()
            db.commit()

            session: dict[str, Any] = {
                "session_id": row.session_id,
                "user_id": row.user_id,
                "data_summary": _parse_json(row.data_summary_json, {}),
                "analysis": _parse_json(row.analysis_json, {}),
                "charts": _parse_json(row.charts_json, []),
                "history": _parse_json(row.history_json, []),
                "active_theme": row.active_theme or "business",
                "style_overrides": _parse_json(row.style_overrides_json, {}),
            }

            # Restore DataFrame from Parquet
            path = self._parquet_path(session_id)
            if os.path.exists(path):
                session["df"] = pd.read_parquet(path)
                print(f"[SessionStore] parquet loaded: {path}")
            else:
                session["df"] = None

            print("[SessionStore] loaded successfully")
            return session
        except Exception:
            print("[SessionStore] ERROR loading session:")
            traceback.print_exc()
            return None
        finally:
            db.close()

    def find(self, session_id: str) -> dict[str, Any] | None:
        """Load a session by session_id alone (no user_id required).
        Used by endpoints that lack authentication (e.g. /export/*).
        """
        print(f"[SessionStore] find — session={session_id}")
        db = SessionLocal()
        try:
            row = db.query(Session).filter(
                Session.session_id == session_id,
            ).first()
            if not row:
                print("[SessionStore] find — not found")
                return None
            return self.load(session_id, row.user_id)
        except Exception:
            print("[SessionStore] ERROR in find:")
            traceback.print_exc()
            return None
        finally:
            db.close()

    def exists(self, session_id: str, user_id: int) -> bool:
        """Check whether a session exists in the store."""
        db = SessionLocal()
        try:
            exists = db.query(Session).filter(
                Session.user_id == user_id,
                Session.session_id == session_id,
            ).first() is not None
            return exists
        except Exception:
            return False
        finally:
            db.close()

    def delete(self, session_id: str, user_id: int) -> bool:
        """Delete a session from both SQLite and disk. Returns True on success."""
        print(f"[SessionStore] delete — session={session_id} user={user_id}")
        db = SessionLocal()
        try:
            row = db.query(Session).filter(
                Session.user_id == user_id,
                Session.session_id == session_id,
            ).first()
            if row:
                db.delete(row)
                db.commit()
                # Remove parquet file
                path = self._parquet_path(session_id)
                if os.path.exists(path):
                    os.unlink(path)
                print("[SessionStore] deleted")
                return True
            print("[SessionStore] not found for deletion")
            return False
        except Exception:
            print("[SessionStore] ERROR deleting session:")
            traceback.print_exc()
            try:
                db.rollback()
            except Exception:
                logger.exception("[SessionStore] rollback failed")
            return False
        finally:
            db.close()

    def cleanup_expired(self, hours: int = 24) -> int:
        """Remove sessions older than `hours` since last access.

        Returns the number of sessions cleaned up.
        """
        print(f"[SessionStore] cleanup_expired — {hours}h threshold")
        db = SessionLocal()
        deleted_count = 0
        try:
            cutoff = datetime.now()
            rows = db.query(Session).all()
            for row in rows:
                try:
                    last = datetime.strptime(row.last_access_at or row.created_at, "%Y-%m-%d %H:%M")
                    if (cutoff - last).total_seconds() > hours * 3600:
                        # Remove parquet
                        path = self._parquet_path(row.session_id)
                        if os.path.exists(path):
                            os.unlink(path)
                        db.delete(row)
                        deleted_count += 1
                except ValueError:
                    pass  # cannot parse date — keep the row
            db.commit()
            print(f"[SessionStore] cleanup_expired — removed {deleted_count} sessions")
            return deleted_count
        except Exception:
            print("[SessionStore] ERROR during cleanup:")
            traceback.print_exc()
            try:
                db.rollback()
            except Exception:
                logger.exception("[SessionStore] rollback failed")
            return 0
        finally:
            db.close()


# ── Internal helpers ────────────────────────────────────────

def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def _parse_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
