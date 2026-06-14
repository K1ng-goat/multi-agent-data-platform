"""AnalysisMemory — long-term analysis KPI, trend, anomaly history."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class AnalysisMemory(Base):
    __tablename__ = "analysis_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), default="")
    kpi_json = Column(Text)
    trend_json = Column(Text)
    anomaly_json = Column(Text)
    report_content = Column(Text)
    created_at = Column(String(255), default="")
