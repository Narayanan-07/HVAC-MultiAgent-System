# Technology Stack
## Multi-Agent HVAC Optimization System
**Version:** 1.0.0 | **Decision Date:** 2026

---

## 1. Stack Overview

```
┌─────────────────────────────────────────────────────┐
│                 ELECTRON FRONTEND                    │
│         (Desktop UI + HTML Report Viewer)            │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / REST
┌──────────────────────▼──────────────────────────────┐
│                  FASTAPI BACKEND                     │
│              (Orchestration Layer)                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               CREWAI AGENT LAYER                     │
│  Agent1 → Agent2 → Agent3 → Agent4 → Agent5         │
└──────────────────────┬──────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  SQLite/PG       ChromaDB         File System
  (Run Logs)    (Vector Memory)   (CSV + Reports)
```

---

## 2. Backend Technologies

### 2.1 Python 3.11+
**Role:** Core runtime for all backend logic, agents, and ML models.

**Justification:**
- Industry standard for ML/AI workloads
- Native support for all required ML libraries (scikit-learn, Prophet, TensorFlow)
- CrewAI is Python-native
- Type hint support (3.10+) for production-grade code quality

**Key packages:**
```
python = "^3.11"
```

---

### 2.2 CrewAI 0.28+
**Role:** Multi-agent orchestration framework — defines agents, tasks, tools, and execution flow.

**Justification:**
- Purpose-built for multi-agent systems with role-based agent design
- Native support for agent memory, tool use, and sequential/hierarchical execution
- Built on LangChain but adds crew-level coordination (agents can pass outputs to each other)
- Supports custom tools — wraps any Python function as an agent-callable tool
- Active development, production-ready as of 2024

**Agent execution modes used:**
- `Process.sequential` — Agents 1 through 5 run in order
- Optional `Process.hierarchical` — Supervisor agent monitors and re-routes failures

**Core structure:**
```python
from crewai import Agent, Task, Crew, Process

crew = Crew(
    agents=[ingestion_agent, analyzer_agent, forecast_agent, optimizer_agent, reporter_agent],
    tasks=[ingest_task, analyze_task, forecast_task, optimize_task, report_task],
    process=Process.sequential,
    verbose=True
)
```

---

### 2.3 FastAPI 0.110+
**Role:** REST API layer — exposes all agent pipelines as HTTP endpoints.

**Justification:**
- Async-first design matches the non-blocking nature of agent pipelines
- Auto-generates OpenAPI docs (Swagger UI) — critical for development and testing
- Pydantic v2 integration for request/response validation
- Significantly faster than Flask for I/O-bound tasks
- Native background task support for long-running agent pipelines

**Key endpoints:**
```
POST /api/v1/pipeline/run        → trigger full 5-agent pipeline
GET  /api/v1/pipeline/status/{id} → poll run status
GET  /api/v1/reports/{run_id}    → fetch generated report
POST /api/v1/data/upload         → upload new CSV dataset
GET  /api/v1/history             → list all historical runs
```

---

### 2.4 ML & Analytics Libraries

#### Pandas 2.0+
**Role:** Core data manipulation — ingestion, cleaning, feature engineering.
**Justification:** Industry standard for tabular data; vectorized operations are fast enough for 30-day hourly datasets (~720 rows per building).

#### NumPy 1.26+
**Role:** Numerical computations — iKW-TR derivation, thermodynamic calculations.
**Justification:** Foundation of all ML libraries; required for Stull WBT equation implementation.

#### Scikit-learn 1.4+
**Role:** Anomaly detection (Isolation Forest), preprocessing (StandardScaler), baseline models.
**Justification:**
- Isolation Forest is purpose-built for unsupervised anomaly detection in multivariate time series
- StandardScaler is essential before any distance-based ML operation
- Consistent `.fit()` / `.predict()` API reduces code complexity

#### Prophet (Meta) 1.1+
**Role:** Primary forecasting model for 24–168 hour energy demand prediction.
**Justification:**
- Handles seasonality (daily, weekly, yearly) natively — critical for HVAC load patterns
- Deals gracefully with missing data and holidays
- Outputs confidence intervals (yhat_lower, yhat_upper) out-of-the-box
- No feature engineering needed for time-based patterns

#### XGBoost 2.0+
**Role:** Secondary forecasting model + anomaly severity scoring.
**Justification:**
- Handles tabular features (weather, occupancy proxy, day type) better than Prophet
- Used as fallback model and for feature importance analysis
- Fast inference — suitable for real-time scoring

#### Matplotlib 3.8+ / Plotly 5.18+
**Role:** Chart generation for reports.
**Justification:** Matplotlib for static PDF charts; Plotly for interactive HTML charts. Both export to base64 for report embedding.

---

## 3. Frontend — Electron 29+

**Role:** Cross-platform desktop application — file upload, pipeline control, report viewer.

**Justification:**
- Single codebase runs on Windows, macOS, Linux — the three OS environments facility managers use
- Renders HTML reports natively (Chromium engine) — no additional viewer needed
- Communicates with FastAPI backend via local HTTP (localhost)
- Node.js integration allows direct file system access for CSV loading
- More appropriate than a web app for a local deployment model (no server needed)

**Frontend stack within Electron:**
```
Electron (shell)
  └── React 18 (UI components)
  └── TailwindCSS (styling)
  └── Axios (API calls to FastAPI)
  └── Recharts (dashboard charts)
```

**Why not a web app instead of Electron?**
Facility managers often operate on isolated internal networks. A desktop app with a local FastAPI backend requires no network configuration, no server, and no authentication complexity.

---

## 4. Data Storage

### 4.1 SQLite (Development) → PostgreSQL (Production-Ready)
**Role:** Persistent storage for run logs, agent outputs, recommendations history.

**Schema overview:**
```
pipeline_runs     → run_id, timestamp, status, duration_s
agent_outputs     → run_id, agent_name, output_json, created_at
recommendations   → run_id, action_type, priority, rationale, expected_savings_kwh
anomaly_log       → run_id, timestamp, parameter, severity, root_cause
forecast_results  → run_id, forecast_horizon_h, predicted_kwh, lower_bound, upper_bound
```

**Justification for SQLite first:**
- Zero configuration, single file, ships with Python
- SQLAlchemy ORM allows drop-in switch to PostgreSQL with one config change
- Sufficient for resume project scale (< 10 buildings, < 1M rows)

**Migration path to PostgreSQL:**
```python
# Development
DATABASE_URL = "sqlite:///./hvac_system.db"

# Production (one-line change)
DATABASE_URL = "postgresql://user:pass@localhost/hvac_db"
```

### 4.2 File System
**Role:** Raw CSV storage, generated PDF/HTML reports.
```
data/
  raw/          → uploaded CSVs
  processed/    → cleaned, feature-engineered CSVs
reports/
  pdf/          → generated PDF reports
  html/         → generated HTML reports
models/
  saved/        → serialized Prophet/XGBoost models
```

---

## 5. Optional Tools

### 5.1 ChromaDB 0.4+
**Role:** Vector database for agent memory — stores past recommendations, anomaly descriptions, and report summaries as embeddings.

**Use case:**
- Agent 4 (Optimizer) queries ChromaDB to avoid recommending the same action repeatedly
- Agent 5 (Reporter) retrieves similar past anomalies to provide historical context in reports
- Enables "conversational memory" if the chat interface is added

**Justification:**
- Runs embedded (no server needed) — fits the local deployment model
- Python-native API: `client.add()` / `client.query()`
- Uses sentence-transformers for embeddings (no API key required)

```python
import chromadb
client = chromadb.Client()  # Embedded, no server
collection = client.create_collection("hvac_recommendations")
```

### 5.2 Weasyprint / ReportLab
**Role:** PDF generation for Decision Reports.
**Choice:** WeasyPrint (HTML → PDF) — allows same template to render both HTML and PDF.

### 5.3 Open-Meteo API (Weather)
**Role:** Free weather forecast API for Agent 3 (Forecasting) — fetches 7-day temperature and humidity forecast for the building's location.
**Justification:** Completely free, no API key required, JSON response, 1-hour resolution.
```
GET https://api.open-meteo.com/v1/forecast
    ?latitude=13.08&longitude=80.27
    &hourly=temperature_2m,relativehumidity_2m,dewpoint_2m
    &forecast_days=7
```

---

## 6. Development & Quality Tools

| Tool | Version | Purpose |
|------|---------|---------|
| `pytest` | 7.4+ | Unit and integration testing |
| `pytest-cov` | 4.1+ | Code coverage reports |
| `black` | 24+ | Code formatting |
| `ruff` | 0.3+ | Fast linting |
| `mypy` | 1.8+ | Static type checking |
| `pre-commit` | 3.6+ | Git hooks for formatting/lint |
| `loguru` | 0.7+ | Structured logging across agents |
| `python-dotenv` | 1.0+ | Environment variable management |
| `httpx` | 0.27+ | Async HTTP client (API tests) |

---

## 7. Complete `requirements.txt`

```
# Core
fastapi==0.110.0
uvicorn[standard]==0.29.0
pydantic==2.6.0
python-dotenv==1.0.1
loguru==0.7.2

# CrewAI
crewai==0.28.0
langchain==0.1.16
langchain-google-genai==1.0.3

# Data & ML
pandas==2.2.1
numpy==1.26.4
scikit-learn==1.4.1
prophet==1.1.5
xgboost==2.0.3
scipy==1.12.0

# Visualization
matplotlib==3.8.3
plotly==5.18.0
kaleido==0.2.1

# Storage
sqlalchemy==2.0.28
alembic==1.13.1
chromadb==0.4.24

# Report Generation
weasyprint==62.1
jinja2==3.1.3

# Testing
pytest==7.4.4
pytest-cov==4.1.0
httpx==0.27.0

# Code Quality
black==24.2.0
ruff==0.3.2
mypy==1.8.0
pre-commit==3.6.2
```
