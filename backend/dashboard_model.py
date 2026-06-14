"""Dashboard snapshot model — stores latest analysis KPI and charts."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, default=0)
    filename = Column(String(255), default="")
    rows = Column(Integer, default=0)
    columns = Column(Integer, default=0)
    kpi = Column(Text)
    charts = Column(Text)
    ai_summary = Column(Text)
    ai_trend = Column(Text)
    ai_anomaly = Column(Text)
    columns_list = Column(Text)
    updated_at = Column(String(255), default="")
