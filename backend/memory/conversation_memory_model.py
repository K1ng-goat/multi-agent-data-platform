"""ConversationMemory — persistent conversation + agent execution history."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String
from database import Base


class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)          # "user" | "ai"
    content = Column(String, default="")
    mode = Column(String, default="chat")          # "chat" | "workflow" | "agent"
    steps_json = Column(String, default="")         # JSON: tool call or agent step history
    created_at = Column(String, default="")
