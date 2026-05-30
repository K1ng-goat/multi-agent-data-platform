"""WorkspaceMemory — persistent workspace state snapshots."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String
from database import Base


class WorkspaceMemory(Base):
    __tablename__ = "workspace_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    filename = Column(String, default="")
    data_summary = Column(String, default="")     # JSON: {shape, columns, dtypes}
    charts_summary = Column(String, default="")    # JSON: [{type, title}]
    analysis_summary = Column(String, default="")  # JSON: {summary, anomaly, trend} abbreviated
    active_theme = Column(String, default="business")
    created_at = Column(String, default="")
    updated_at = Column(String, default="")
