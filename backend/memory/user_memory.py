"""UserMemory service — manages persistent user preferences and behavior patterns."""
from __future__ import annotations
import json
import traceback
from datetime import datetime
from database import SessionLocal
from memory.user_memory_model import UserMemory


def save_user_memory(user_id: int, category: str, key: str, value: str) -> None:
    """Upsert a user memory entry."""
    print(f"[Memory User] save_user_memory — user={user_id} cat={category} key={key}")
    db = SessionLocal()
    try:
        row = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.category == category,
            UserMemory.key == key,
        ).first()
        if row:
            row.value = value
            row.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            print("[Memory User] updating existing row")
        else:
            db.add(UserMemory(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ))
            print("[Memory User] inserting new row")
        db.commit()
        print("[Memory User] commit OK")
    except Exception:
        print("[Memory User] ERROR on save_user_memory:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def get_user_memories(user_id: int, category: str | None = None) -> dict[str, str]:
    """Get all user memories, optionally filtered by category. Returns {key: value} dict."""
    print(f"[Memory User] get_user_memories — user={user_id} category={category}")
    db = SessionLocal()
    try:
        q = db.query(UserMemory).filter(UserMemory.user_id == user_id)
        if category:
            q = q.filter(UserMemory.category == category)
        rows = q.all()
        print(f"[Memory User] get_user_memories — found {len(rows)} rows")
        return {row.key: row.value for row in rows}
    except Exception:
        print("[Memory User] ERROR on get_user_memories:")
        traceback.print_exc()
        return {}
    finally:
        db.close()


def get_user_memory(user_id: int, category: str, key: str) -> str | None:
    """Get a single user memory value."""
    db = SessionLocal()
    try:
        row = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.category == category,
            UserMemory.key == key,
        ).first()
        return row.value if row else None
    except Exception:
        print("[Memory User] ERROR on get_user_memory:")
        traceback.print_exc()
        return None
    finally:
        db.close()


def delete_user_memory(user_id: int, category: str, key: str) -> bool:
    """Delete a user memory entry. Returns True if deleted."""
    db = SessionLocal()
    try:
        row = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.category == category,
            UserMemory.key == key,
        ).first()
        if row:
            db.delete(row)
            db.commit()
            return True
        return False
    except Exception:
        print("[Memory User] ERROR on delete_user_memory:")
        traceback.print_exc()
        return False
    finally:
        db.close()


def clear_preferences(user_id: int) -> int:
    """Delete all user preference memories for a user. Returns count deleted."""
    print(f"[Memory User] clear_preferences — user={user_id}")
    db = SessionLocal()
    try:
        count = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.category == "preference",
        ).delete()
        db.commit()
        print(f"[Memory User] clear_preferences — deleted {count} rows")
        return count
    except Exception:
        print("[Memory User] ERROR on clear_preferences:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        return 0
    finally:
        db.close()


def extract_preferences(user_id: int) -> dict:
    """Extract structured user preferences for agent context injection."""
    print(f"[Memory User] extract_preferences — user={user_id}")
    memories = get_user_memories(user_id)
    prefs = {}
    for key, val in memories.items():
        try:
            prefs[key] = json.loads(val)
        except Exception:
            prefs[key] = val
    print(f"[Memory User] extract_preferences — {len(prefs)} keys extracted")
    return prefs
