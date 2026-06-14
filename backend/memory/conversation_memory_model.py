"""ConversationMemory — persistent conversation + agent execution history."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(255), nullable=False)
    content = Column(Text)
    mode = Column(String(255), default="chat")
    steps_json = Column(Text)
    created_at = Column(String(255), default="")
