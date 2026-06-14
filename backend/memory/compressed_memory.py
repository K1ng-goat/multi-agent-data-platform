"""CompressedMemory ORM — stores summarized memory snapshots."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String
from database import Base


class CompressedMemory(Base):
    __tablename__ = "compressed_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    memory_type = Column(String(50), nullable=False)    # "conversation" | "analysis"
    summary = Column(String(2000), default="")
    item_count = Column(Integer, default=0)
    compressed_count = Column(Integer, default=0)
    created_at = Column(String(24), default="")
