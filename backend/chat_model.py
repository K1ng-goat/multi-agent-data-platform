"""Chat message model — persists conversation history."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, default=0)
    role = Column(String, nullable=False)
    content = Column(Text, default="")
    created_at = Column(String, default="")
