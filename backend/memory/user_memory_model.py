"""UserMemory — persistent user preferences and behavior patterns."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String(255), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)           # JSON-encoded value
    updated_at = Column(String(255), default="")
