# 🧠 Multi-Agent Data Platform

<div align="center">

**AI-powered Excel data analysis platform with autonomous multi-agent orchestration**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev)
[![Tailwind](https://img.shields.io/badge/Tailwind-4-38bdf8?logo=tailwindcss)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/license-MIT-purple)](LICENSE)

</div>

---

## 📖 Project Overview

**Multi-Agent Data Platform** is an intelligent Excel data analysis platform that transforms natural language into comprehensive analytical actions. Instead of a monolithic LLM call, the system employs a **Master Agent** that classifies user intent, decomposes tasks, and orchestrates 6 specialized sub-agents through a shared context pipeline.

> Upload an Excel file → AI autonomously analyzes, charts, audits, styles, and exports — all without manual intervention.

---

## 🏗️ Agent Architecture

```
User Input (Natural Language)
       │
       ▼
┌─────────────────────────────────────┐
│         DataMasterAgent              │
│   • Intent Classification            │
│   • Task Planning & Routing          │
│   • Pipeline Orchestration           │
└──────────┬──────────────────────────┘
           │ INTENT_AGENT_MAP
           ▼
┌──────────┼──────────┬──────────┬──────────┬──────────┐
│   Data   │  Chart   │  Audit   │  Report  │  Style   │ Export  │
│  Agent   │  Agent   │  Agent   │  Agent   │  Agent   │ Agent   │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ ◆ Stats  │◆ Line    │◆ Null    │◆ Markdown│◆ Theme   │◆ Excel  │
│ ◆ AI     │◆ Bar     │◆ Dup     │◆ Summary │◆ Font    │◆ Word   │
│ ◆ Trend  │◆ Pie     │◆ Z-score │◆ KPI     │◆ Color   │◆ PNG    │
│ ◆ Anomaly│          │◆ Score   │          │          │         │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
       │          │          │          │          │          │
       └──────────┴──────────┴──────────┴──────────┴──────────┘
                           │
                   Shared Context dict
                           │
                           ▼
              ┌──────────────────────┐
              │   Workflow Engine    │
              │  Format Response     │
              │  500KB Hard Limit    │
              └──────────────────────┘
```

| Agent | Role | Key Capabilities |
|-------|------|------------------|
| **MasterAgent** | Orchestrator | Intent classification (8 types), task decomposition, pipeline execution |
| **DataAgent** | Analyst | Statistical summary, DeepSeek AI analysis, trend & anomaly detection |
| **ChartAgent** | Visualizer | Line/Bar/Pie chart generation, automatic chart type recommendation |
| **AuditAgent** | Auditor | Data quality scoring, null/duplicate/outlier detection, Z-score analysis |
| **ReportAgent** | Writer | Markdown report generation via DeepSeek, KPI extraction |
| **StyleAgent** | Designer | Theme detection, Chinese font/size/color parsing, style application |
| **ExportAgent** | Exporter | Excel (.xlsx 3-sheet), Word (.docx), Chart images (.png) |

---

## 🧠 AI Memory System (RAG)

A 4-layer memory architecture provides **retrieval-augmented generation** context to every AI interaction:

```
┌──────────────────────────────────────────┐
│              Memory Manager               │
├──────────────┬──────────────┬────────────┤
│  User Memory │  Workspace   │Conversation│
│  (Preferences│   Memory     │   Memory   │
│  key-value)  │ (Snapshots)  │ (History)  │
├──────────────┴──────────────┴────────────┤
│         Long-term Analysis Memory         │
│    (KPI, Trend, Anomaly, Full Reports)    │
└──────────────────────────────────────────┘
```

- **Retrieve** relevant memories before each agent execution
- **Inject** memory context into LLM prompts
- **Learn** user preferences from repeated interactions
- **Search** historical analyses by keyword

---

## 🛠️ Tech Stack

### Backend

| Technology | Usage |
|-----------|-------|
| **FastAPI** + Uvicorn | REST API server with async support |
| **pandas** | Excel parsing, data manipulation, statistical computation |
| **SQLAlchemy** + SQLite | ORM with 9-table schema |
| **python-jose** + passlib/bcrypt | JWT authentication (HS256, 7-day expiry) |
| **httpx** | Async HTTP client for DeepSeek API calls |
| **openpyxl** / **python-docx** | Excel & Word file export |
| **matplotlib** | Chart rendering to PNG |
| **DeepSeek API** | LLM for analysis, report generation, style parsing |

### Frontend

| Technology | Usage |
|-----------|-------|
| **Next.js 16** (App Router) | React framework with Turbopack |
| **React 19** | UI components with hooks |
| **TypeScript 5** | Type-safe frontend |
| **Recharts** | Interactive Line, Bar, Pie charts |
| **Tailwind CSS v4** | Utility-first styling with dark mode |
| **React Context** + localStorage | State management & workspace persistence |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **DeepSeek API Key** — Get one at [platform.deepseek.com](https://platform.deepseek.com)

### 1. Clone & Setup Backend

```bash
cd data-agent/backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
set DEEPSEEK_API_KEY=sk-your-key-here        # Windows
export DEEPSEEK_API_KEY=sk-your-key-here      # macOS/Linux

# Start the server
python main.py
```

Backend runs at **http://localhost:8000**

### 2. Setup Frontend

```bash
cd data-agent/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at **http://localhost:3000**

### 3. Start Analyzing

1. Open **http://localhost:3000** in your browser
2. Register an account
3. Upload an Excel file in Workspace
4. Ask questions in natural language — the AI agent team does the rest

---

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | **Yes** | — | DeepSeek API key for LLM features |
| `JWT_SECRET` | No | Built-in fallback | Secret key for JWT token signing |

---

## 📂 Project Structure

```
data-agent/
├── backend/
│   ├── main.py                  # FastAPI app (25+ endpoints)
│   ├── database.py              # SQLAlchemy engine & table init
│   ├── auth_service.py          # JWT + bcrypt authentication
│   ├── workflow.py              # Workflow planner (DeepSeek-driven)
│   ├── workflow_engine.py       # Multi-agent orchestration engine
│   ├── export_service.py        # Excel/Word/Chart export
│   ├── dashboard_service.py     # KPI & chart aggregation
│   ├── reports_service.py       # Report history CRUD
│   ├── theme_service.py         # Style theme system (4 presets)
│   ├── style_config.py          # Live style configuration
│   ├── agents/                  # Multi-Agent System
│   │   ├── base_agent.py        # Abstract base class
│   │   ├── data_master_agent.py # Master orchestrator
│   │   ├── data_agent.py        # Data analysis agent
│   │   ├── chart_agent.py       # Chart generation agent
│   │   ├── audit_agent.py       # Data quality audit agent
│   │   ├── report_agent.py      # Report generation agent
│   │   ├── style_agent.py       # Style/theme agent
│   │   └── export_agent.py      # File export agent
│   ├── memory/                  # AI Memory System (4-layer)
│   │   ├── memory_manager.py    # Central orchestrator
│   │   ├── user_memory.py       # User preferences (key-value)
│   │   ├── workspace_memory.py  # Workspace snapshots
│   │   ├── conversation_memory.py # Chat history
│   │   └── longterm_memory.py   # KPI & trend history
│   ├── models/                  # SQLAlchemy ORM models
│   └── exports/                 # Generated export files
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Workspace (main page)
│   │   │   ├── analytics/       # Home / Overview dashboard
│   │   │   ├── reports/         # History center
│   │   │   ├── memory/          # AI memory management
│   │   │   ├── login/           # Auth pages
│   │   │   └── register/
│   │   │   └── components/      # Shared components
│   │   │       ├── NavBar.tsx
│   │   │       ├── ClientLayout.tsx
│   │   │       └── ErrorBoundary.tsx
│   │   └── lib/
│   │       ├── api.ts            # API fetch wrapper
│   │       ├── AuthContext.tsx   # Auth state
│   │       └── WorkspaceContext.tsx # Workspace persistence
│   ├── package.json
│   └── next.config.js
│
├── .gitignore
└── README.md
```

---

## ✨ Features

### 📊 Data Analysis
- Upload Excel files and get instant AI-powered analysis
- Statistical summary with describe(), correlation, null counts
- Trend detection and anomaly flagging via Z-score
- Built-in data profiling with column dtypes and shape info

### 🤖 Multi-Agent Pipeline
- **8 intent types** auto-classified from natural language
- Master Agent routes to the right sub-agents automatically
- Shared context flows through entire execution pipeline
- Frontend visualizes each agent step with status badges

### 📈 Charts & Visualization
- Auto-generated Line, Bar, and Pie charts
- Interactive Recharts components with responsive sizing
- Chart export to PNG via matplotlib
- Dark mode support across all visualizations

### 🔍 Data Quality Audit
- Completeness check (null percentage per column)
- Duplicate row detection
- Z-score based outlier detection
- Composite quality score (0-100)

### 🎨 Style & Theme System
- 4 preset themes: Business, Simple, Dark, Academic
- Chinese natural language style commands
- AI-powered style parsing for complex requests
- Live style configuration applied to exports

### 📤 Export
- **Excel**: 3-sheet workbook (data, analysis, statistics)
- **Word**: Professional report with charts and styling
- **Chart**: PNG/JPEG image export

### 🧠 AI Memory
- 4-layer memory for persistent AI context
- User preference learning from repeated interactions
- Keyword search across historical analyses
- Memory management with clear/reset controls

### 🔐 Security
- JWT Bearer token authentication
- bcrypt password hashing
- CORS restriction for localhost origins
- API endpoints protected via FastAPI dependency injection

---

## 📸 Screenshots

<!-- Screenshots placeholder — add your screenshots here -->
<p align="center">
  <em>Workspace — Upload Excel files and chat with AI agents</em><br/>
  <img src="docs/screenshots/workspace.png" width="800" alt="Workspace"/>
</p>

<p align="center">
  <em>Home Dashboard — KPIs, charts, and AI analysis summary</em><br/>
  <img src="docs/screenshots/home.png" width="800" alt="Home Dashboard"/>
</p>

<p align="center">
  <em>Reports — Unified history center for all analysis results</em><br/>
  <img src="docs/screenshots/reports.png" width="800" alt="Reports"/>
</p>

<p align="center">
  <em>Memory — AI preferences and memory management</em><br/>
  <img src="docs/screenshots/memory.png" width="800" alt="Memory"/>
</p>

---

## 🔗 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register` | User registration |
| `POST` | `/login` | User login |
| `GET` | `/me` | Current user info |

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload Excel file |
| `POST` | `/analyze` | Upload + full AI analysis |
| `POST` | `/chat` | Chat with tool-calling |
| `POST` | `/agent-chat` | Multi-agent pipeline |

### Dashboard & Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard` | KPI dashboard data |
| `GET` | `/reports` | List historical reports |
| `GET` | `/reports/{id}` | Get single report |

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/memory/summary` | Aggregated memory stats |
| `GET` | `/memory/recent` | Recent analyses & workspaces |
| `GET` | `/memory/retrieve` | Retrieve memory context |
| `GET/POST` | `/memory/preferences` | User preferences CRUD |
| `DELETE` | `/memory/preferences` | Delete preference |
| `POST` | `/memory/clear` | Clear memory by type |

### Style & Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/themes` | List available themes |
| `POST` | `/style/apply` | Apply theme |
| `GET` | `/style/preview/{id}` | Preview style config |
| `GET` | `/export/excel/{id}` | Download Excel |
| `GET` | `/export/word/{id}` | Download Word |
| `GET` | `/export/chart/{id}/{idx}` | Download chart PNG |

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ using FastAPI, Next.js, and DeepSeek</sub>
</div>
