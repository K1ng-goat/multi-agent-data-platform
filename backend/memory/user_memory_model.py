"""UserMemory — persistent user preferences and behavior patterns."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String
from database import Base


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String, nullable=False)   # "style", "export", "analysis", "language", "behavior"
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)       # JSON-encoded value
    updated_at = Column(String, default="")
