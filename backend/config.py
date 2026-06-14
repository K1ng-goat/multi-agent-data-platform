"""Centralized configuration — all tunable values in one place."""
from __future__ import annotations
import os

# ── Server ─────────────────────────────────────────────────────────
API_TITLE = "AI Excel Data Agent"
API_VERSION = "0.1.0"
HOST = "0.0.0.0"
PORT = 8000

# ── CORS ──────────────────────────────────────────────────────────
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
CORS_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1):\d{4}$"

# ── Database ──────────────────────────────────────────────────────
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")  # "sqlite" | "mysql"
DB_FILENAME = "data_agent.db"
DB_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), DB_FILENAME)}"

# MySQL (only used when DB_ENGINE=mysql)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "data_agent")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "changeme")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "data_agent")

# ── JWT ───────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "aiexcel-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

# ── DeepSeek API ──────────────────────────────────────────────────
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT_SEC = 30.0

# ── File Upload ───────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# ── Rate Limiting ─────────────────────────────────────────────────
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 10       # max requests per window
RATE_LIMIT_WINDOW_SEC = 60     # time window in seconds
RATE_LIMITED_ENDPOINTS = ["/chat", "/agent-chat", "/analyze"]

# ── Response ──────────────────────────────────────────────────────
MAX_RESPONSE_BYTES = 500 * 1024   # 500 KB (used by workflow_engine)

# ── Export ────────────────────────────────────────────────────────
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
SESSION_DATA_DIR = os.path.join(os.path.dirname(__file__), "session_data")
