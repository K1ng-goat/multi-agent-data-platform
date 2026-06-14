"""Report model — stores each analysis result for history."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, default=0)
    filename = Column(String(255), default="")
    rows = Column(Integer, default=0)
    columns = Column(Integer, default=0)
    columns_list = Column(Text)
    summary = Column(Text)
    anomaly = Column(Text)
    trend = Column(Text)
    charts = Column(Text)
    created_at = Column(String(255), default="")
