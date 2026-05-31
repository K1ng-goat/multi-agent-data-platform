"""ConversationMemory service — persistent conversation and agent execution history."""
from __future__ import annotations
import json
import logging
import traceback
from datetime import datetime
from database import SessionLocal
from memory.conversation_memory_model import ConversationMemory

logger = logging.getLogger(__name__)


MAX_CONTENT_LENGTH = 10000  # D6: raised from 2000 to prevent silent report truncation


def save_message(user_id: int, session_id: str, role: str, content: str,
                 mode: str = "chat", steps: list | None = None) -> None:
    """Persist a single conversation message."""
    print(f"[Memory Conv] save_message — user={user_id} session={session_id} role={role} mode={mode}")
    db = SessionLocal()
    try:
        truncated_content = content if content else ""
        if len(truncated_content) > MAX_CONTENT_LENGTH:
            logger.warning(
                "[Memory Conv] save_message — content truncated (%d → %d chars) for session=%s role=%s",
                len(truncated_content), MAX_CONTENT_LENGTH, session_id, role,
            )
            truncated_content = truncated_content[:MAX_CONTENT_LENGTH]
        db.add(ConversationMemory(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=truncated_content,
            mode=mode,
            steps_json=json.dumps(steps or [], ensure_ascii=False),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        print("[Memory Conv] committing...")
        db.commit()
        print("[Memory Conv] commit OK")
    except Exception:
        print("[Memory Conv] ERROR on save_message:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            logger.exception("[Memory Conv] ERROR during rollback in save_message")
    finally:
        db.close()


def get_conversation(user_id: int, session_id: str, limit: int = 50) -> list[dict]:
    """Get conversation history for a session."""
    print(f"[Memory Conv] get_conversation — user={user_id} session={session_id}")
    db = SessionLocal()
    try:
        rows = db.query(ConversationMemory).filter(
            ConversationMemory.user_id == user_id,
            ConversationMemory.session_id == session_id,
        ).order_by(ConversationMemory.id.asc()).limit(limit).all()
        print(f"[Memory Conv] get_conversation — found {len(rows)} rows")
        return [_row_to_dict(r) for r in rows]
    except Exception:
        print("[Memory Conv] ERROR on get_conversation:")
        traceback.print_exc()
        return []
    finally:
        db.close()


def get_recent_conversations(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent conversation messages across all sessions (both user + AI).

    D4: Removed role="user" filter — now returns full bidirectional
    conversation history so the AI memory context includes both sides.
    """
    print(f"[Memory Conv] get_recent_conversations — user={user_id}")
    db = SessionLocal()
    try:
        rows = db.query(ConversationMemory).filter(
            ConversationMemory.user_id == user_id,
        ).order_by(ConversationMemory.id.desc()).limit(limit).all()
        print(f"[Memory Conv] get_recent_conversations — found {len(rows)} rows")
        return [_row_to_dict(r) for r in rows]
    except Exception:
        print("[Memory Conv] ERROR on get_recent_conversations:")
        traceback.print_exc()
        return []
    finally:
        db.close()


def _row_to_dict(row: ConversationMemory) -> dict:
    steps = []
    if row.steps_json:
        try:
            steps = json.loads(row.steps_json)
        except Exception:
            print(f"[Memory Conv] ERROR parsing steps_json for id={row.id}:")
            traceback.print_exc()
    return {
        "id": row.id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "role": row.role,
        "content": row.content,
        "mode": row.mode,
        "steps": steps,
        "created_at": row.created_at,
    }
