"""Session ORM model — persisted session metadata.

The raw DataFrame is stored as a Parquet file alongside this table;
only lightweight JSON-serializable metadata lives in SQLite.
"""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(24), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), default="")
    data_summary_json = Column(Text)
    analysis_json = Column(Text)
    charts_json = Column(Text)
    history_json = Column(Text)
    active_theme = Column(String(20), default="business")
    style_overrides_json = Column(Text)
    created_at = Column(String(24), default="")
    last_access_at = Column(String(24), default="")
