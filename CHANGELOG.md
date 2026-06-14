# Changelog

## v1.0.0 (2026-06-04)

### Added
- **Multi-Agent Architecture**: 7-agent system (Master + Data/Chart/Audit/Report/Style/Export)
- **AI Memory System**: 4-layer memory (User, Workspace, Conversation, Long-term Analysis)
- **Session Persistence**: L1 (dict) + L2 (SessionStore/parquet) cache-through architecture
- **Rate Limiting**: 10 req/min on /chat, /agent-chat, /analyze
- **File Upload Validation**: .xlsx/.xls only, MIME type check, 50MB limit
- **Unified Intent Classifier**: Single-source-of-truth for 9 intent types
- **Docker Support**: Backend + Frontend containers, MySQL service definition
- **MySQL Integration**: DB_ENGINE branching, 56 ORM fixes, backward-compatible
- **Database Optimization**: SQLite WAL mode, FK pragma enforcement
- **Preference Dual-Write**: user_preferences + user_memories sync
- **Info Architecture**: Home/Workspace/Reports/Memory page reorganization

### Fixed
- **Memory System**: Category filter for preferences, bidirectional conversations, content limit raised to 10000, except logging
- **Docker UTF-8**: C.UTF-8 locale, PYTHONIOENCODING=utf-8
- **Rate Limit Format**: "10 per 60s" → "10/minute" (limits library compat)
- **Dockerfile apt**: libfreetype6-dev → libfreetype-dev (Debian Bookworm)
- **Frontend Docker**: npm mirror workaround for blocked registry
- **Error Boundary**: React component crash isolation
- **Response Safety**: 500KB hard limit, DataFrame serialization protection

### Changed
- **Auth**: /workflow now requires JWT (was unauthenticated)
- **FastAPI**: 25→29 endpoints
- **Database**: 9→10 tables (added sessions)
- **ORM**: All VARCHAR with explicit length, TEXT without defaults

### Known Limitations
- MySQL runtime not tested (Docker Hub network)
- No automated test suite
- print() logging (not structured)
- Export endpoints have no auth (by design)

---

## v0.1.0 (2026-05-31)

### Initial Release
- FastAPI backend with JWT auth
- Excel upload + pandas analysis
- DeepSeek AI integration (chat, analysis, workflow)
- Recharts frontend (Line/Bar/Pie charts)
- Style/theme system (4 presets)
- Export (Excel, Word, PNG)
- Dashboard + Reports
- Basic memory system (pre-category-fix)
