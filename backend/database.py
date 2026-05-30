"""SQLite + SQLAlchemy database engine and session factory."""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.path.join(os.path.dirname(__file__), "data_agent.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables if they don't exist."""
    import user_model        # noqa: F811 — register User
    import report_model      # noqa: F811 — register Report
    import chat_model        # noqa: F811 — register ChatMessage
    import dashboard_model   # noqa: F811 — register DashboardSnapshot
    import preference_model  # noqa: F811 — register UserPreference
    from memory import user_memory_model        # noqa: F811
    from memory import workspace_memory_model    # noqa: F811
    from memory import conversation_memory_model # noqa: F811
    from memory import analysis_memory_model     # noqa: F811
    Base.metadata.create_all(bind=engine)
