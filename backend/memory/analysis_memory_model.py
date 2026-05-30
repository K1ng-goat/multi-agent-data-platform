"""AnalysisMemory — long-term analysis KPI, trend, anomaly history."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String
from database import Base


class AnalysisMemory(Base):
    __tablename__ = "analysis_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    filename = Column(String, default="")
    kpi_json = Column(String, default="")           # JSON: key metrics extracted from analysis
    trend_json = Column(String, default="")          # JSON: trend data summary
    anomaly_json = Column(String, default="")        # JSON: anomaly findings
    report_content = Column(String, default="")      # Full report markdown
    created_at = Column(String, default="")
