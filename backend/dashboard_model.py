"""Dashboard snapshot model — stores latest analysis KPI and charts."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, default=0)
    filename = Column(String, default="")
    rows = Column(Integer, default=0)
    columns = Column(Integer, default=0)
    kpi = Column(Text, default="{}")
    charts = Column(Text, default="[]")
    ai_summary = Column(Text, default="")
    ai_trend = Column(Text, default="")
    ai_anomaly = Column(Text, default="")
    columns_list = Column(Text, default="[]")
    updated_at = Column(String, default="")
