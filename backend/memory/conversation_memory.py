"""ConversationMemory service — persistent conversation and agent execution history."""
from __future__ import annotations
import json
import traceback
from datetime import datetime
from database import SessionLocal
from memory.conversation_memory_model import ConversationMemory


def save_message(user_id: int, session_id: str, role: str, content: str,
                 mode: str = "chat", steps: list | None = None) -> None:
    """Persist a single conversation message."""
    print(f"[Memory Conv] save_message — user={user_id} session={session_id} role={role} mode={mode}")
    db = SessionLocal()
    try:
        db.add(ConversationMemory(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content[:2000] if content else "",
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
            pass
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
    """Get recent conversation summaries across all sessions."""
    print(f"[Memory Conv] get_recent_conversations — user={user_id}")
    db = SessionLocal()
    try:
        rows = db.query(ConversationMemory).filter(
            ConversationMemory.user_id == user_id,
            ConversationMemory.role == "user",
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
