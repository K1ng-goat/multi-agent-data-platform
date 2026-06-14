"""WorkspaceMemory — persistent workspace state snapshots."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class WorkspaceMemory(Base):
    __tablename__ = "workspace_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), default="")
    data_summary = Column(Text)
    charts_summary = Column(Text)
    analysis_summary = Column(Text)
    active_theme = Column(String(255), default="business")
    created_at = Column(String(255), default="")
    updated_at = Column(String(255), default="")
