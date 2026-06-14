"""SQLAlchemy database engine and session factory.

Supports SQLite (default) and MySQL via DATABASE_TYPE env var:
  DATABASE_TYPE=sqlite  → file-based SQLite (zero-config)
  DATABASE_TYPE=mysql   → MySQL 8.x via PyMySQL

Also reads DB_ENGINE for backward compat (T16).
Falls back to SQLite if pymysql is not installed or MySQL is unreachable.
"""
from __future__ import annotations
import os
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

# T45: DATABASE_TYPE is the canonical name; DB_ENGINE is backward compat
DB_ENGINE = os.getenv("DATABASE_TYPE") or os.getenv("DB_ENGINE", "sqlite")


def get_database_url() -> str:
    """Return the database connection URL for the current engine type."""
    if DB_ENGINE == "mysql":
        return (
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'data_agent')}"
            f":{os.getenv('MYSQL_PASSWORD', 'changeme')}"
            f"@{os.getenv('MYSQL_HOST', 'localhost')}"
            f":{os.getenv('MYSQL_PORT', '3306')}"
            f"/{os.getenv('MYSQL_DATABASE', 'data_agent')}"
        )
    DB_PATH = os.path.join(os.path.dirname(__file__), "data_agent.db")
    return f"sqlite:///{DB_PATH}"


def _try_create_mysql_engine():
    """Attempt MySQL engine creation. Returns None if pymysql not installed."""
    try:
        import pymysql  # noqa: F401
        url = get_database_url()
        return create_engine(url, pool_size=5, max_overflow=10, pool_pre_ping=True)
    except ImportError:
        print("[database] pymysql not installed — falling back to SQLite")
        return None
    except Exception as e:
        print(f"[database] MySQL unavailable ({e}) — falling back to SQLite")
        return None


def _create_sqlite_engine():
    DB_PATH = os.path.join(os.path.dirname(__file__), "data_agent.db")
    eng = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    return eng


# ── Engine Selection ──────────────────────────────────────

if DB_ENGINE == "mysql":
    engine = _try_create_mysql_engine()
    if engine is None:
        # Auto-fallback to SQLite
        os.environ["DATABASE_TYPE"] = "sqlite"
        DB_ENGINE = "sqlite"
        engine = _create_sqlite_engine()
else:
    engine = _create_sqlite_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_database_info() -> dict:
    """Return database metadata for the /database/info endpoint."""
    try:
        tables = inspect(engine).get_table_names()
    except Exception:
        tables = []
    return {
        "database_type": DB_ENGINE,
        "engine": "MySQL" if DB_ENGINE == "mysql" else "SQLite",
        "tables": len(tables),
        "url": str(engine.url).replace("//data_agent:", "//***:***@") if DB_ENGINE == "mysql" else str(engine.url),
    }


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
    import session_model    # noqa: F811 — register Session
    from memory import compressed_memory  # noqa: F811 — T37
    Base.metadata.create_all(bind=engine)
