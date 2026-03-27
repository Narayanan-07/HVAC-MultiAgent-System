# System Design Document
## Multi-Agent HVAC Optimization System
**Version:** 1.0.0 | **Type:** Architecture & Design Reference

---

## 1. System Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                        ELECTRON DESKTOP APP                          ║
║  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  ║
║  │  Upload CSV  │  │  Dashboard   │  │   HTML Report Viewer      │  ║
║  │  (Data In)   │  │  (Status)    │  │   (Embedded Chromium)     │  ║
║  └──────┬───────┘  └──────┬───────┘  └────────────┬──────────────┘  ║
╚═════════╪════════════════╪═══════════════════════╪══════════════════╝
          │   HTTP/REST    │                        │
          ▼                ▼                        ▼
╔══════════════════════════════════════════════════════════════════════╗
║                      FASTAPI BACKEND                                  ║
║                                                                       ║
║   POST /api/v1/pipeline/run      GET /api/v1/reports/{id}            ║
║   GET  /api/v1/pipeline/status   POST /api/v1/data/upload            ║
║                                                                       ║
║   ┌──────────────────────────────────────────────────────────────┐   ║
║   │               PIPELINE ORCHESTRATOR                          │   ║
║   │   Validates input → Spawns CrewAI Crew → Polls status        │   ║
║   └──────────────────────────┬───────────────────────────────────┘   ║
╚════════════════════════════╪═════════════════════════════════════════╝
                             │
╔════════════════════════════▼═════════════════════════════════════════╗
║                     CREWAI AGENT LAYER                                ║
║                                                                       ║
║  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐           ║
║  │ AGENT 1 │──▶│ AGENT 2  │──▶│ AGENT 3  │──▶│ AGENT 4  │──▶ ...   ║
║  │ Ingest  │   │ Analyze  │   │ Forecast │   │ Optimize │           ║
║  └────┬────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘           ║
║       │             │               │               │                 ║
║  [Tool: CSV   [Tool: IsoForest  [Tool: Prophet  [Tool: Rules          ║
║   Parser]      Z-Score]         XGBoost]        Engine]              ║
║                                                                       ║
║                                          ┌──────────┐                ║
║                                          │ AGENT 5  │                ║
║                                          │  Report  │                ║
║                                          └────┬─────┘                ║
║                                          [Tool: WeasyPrint            ║
║                                           Jinja2 + Plotly]           ║
╚═══════════════════════════════════════════╪══════════════════════════╝
                                            │
                    ┌───────────────────────┼────────────────────┐
                    ▼                       ▼                    ▼
             ┌────────────┐         ┌─────────────┐      ┌────────────┐
             │  SQLite DB │         │  ChromaDB   │      │ File Store │
             │ (Run Logs) │         │ (Embeddings)│      │ CSV/Reports│
             └────────────┘         └─────────────┘      └────────────┘
                                            │
                                    ┌───────▼──────┐
                                    │ Open-Meteo   │
                                    │ Weather API  │
                                    └──────────────┘
```

---

## 2. Agent Design

### Agent 1 — Data Ingestion & Preprocessing Agent

```
Role       : Data Engineer
Goal       : Transform raw CSVs into a clean, analysis-ready dataframe
Backstory  : Expert in building energy data pipelines and sensor data quality
```

**Responsibilities:**
- Load BDG2 `chilledwater.csv`, `weather.csv`, `metadata.csv`
- Align timestamps, fill gaps using forward-fill / interpolation
- Derive iKW-TR: `Power_kW / Cooling_Tons`
- Derive WBT from dry-bulb temp + humidity (Stull equation)
- Engineer features: `hour_of_day`, `day_of_week`, `is_weekend`, `rolling_avg_24h`
- Flag data quality issues in a `data_quality_report` dict
- Output: `clean_df` (Pandas DataFrame) written to `data/processed/`

**Tools:**
```python
@tool("CSV Loader")
def load_and_merge_datasets(data_path: str) -> pd.DataFrame: ...

@tool("Feature Engineer")
def engineer_hvac_features(df: pd.DataFrame) -> pd.DataFrame: ...

@tool("WBT Calculator")
def derive_wet_bulb_temperature(temp_c: float, humidity_pct: float) -> float: ...
```

---

### Agent 2 — Performance Analyzer Agent

```
Role       : HVAC Performance Diagnostician
Goal       : Identify what is wrong, how bad it is, and why
Backstory  : Senior MEP engineer with expertise in chiller plant diagnostics
```

**Responsibilities:**
- Compute actual iKW-TR vs. benchmark (0.60 kW/TR industry standard)
- Run Isolation Forest on 4-parameter matrix (kWh, iKW-TR, temp, humidity)
- Apply Z-score (|Z| > 3.0) for univariate anomaly confirmation
- Classify root cause: weather-driven / equipment-driven / behavioral
- Score degradation trend over 7-day and 30-day windows
- Output: `anomaly_report` JSON with severity, timestamps, root causes

**Tools:**
```python
@tool("Isolation Forest Detector")
def detect_anomalies_isolation_forest(df: pd.DataFrame) -> pd.DataFrame: ...

@tool("Z-Score Validator")
def validate_anomalies_zscore(df: pd.DataFrame, column: str) -> pd.DataFrame: ...

@tool("Root Cause Classifier")
def classify_root_cause(anomaly_row: dict, df: pd.DataFrame) -> str: ...

@tool("Degradation Trend Scorer")
def score_degradation_trend(df: pd.DataFrame, window_days: int) -> dict: ...
```

---

### Agent 3 — Forecasting Agent

```
Role       : Energy Demand Forecaster
Goal       : Predict future HVAC energy consumption with quantified uncertainty
Backstory  : Data scientist specializing in time-series energy forecasting
```

**Responsibilities:**
- Fit Prophet model on historical kWh + weather features
- Generate 24-hour forecast (operational planning)
- Generate 168-hour (7-day) forecast (maintenance scheduling)
- Fetch live weather forecast from Open-Meteo API for forecast horizon
- Output confidence intervals (80% CI, 95% CI) per hour
- Fallback to XGBoost if Prophet fails (insufficient data)

**Tools:**
```python
@tool("Prophet Forecaster")
def run_prophet_forecast(df: pd.DataFrame, horizon_hours: int) -> dict: ...

@tool("XGBoost Forecaster")
def run_xgboost_forecast(df: pd.DataFrame, horizon_hours: int) -> dict: ...

@tool("Weather API Fetcher")
def fetch_weather_forecast(lat: float, lon: float, days: int) -> pd.DataFrame: ...

@tool("Peak Demand Predictor")
def predict_peak_demand_windows(forecast_df: pd.DataFrame) -> list: ...
```

---

### Agent 4 — Optimization & Recommendation Agent

```
Role       : HVAC Optimization Engineer
Goal       : Convert analytical insights into safe, explainable operational actions
Backstory  : Energy consultant who has optimized HVAC systems across 50+ commercial buildings
```

**Responsibilities:**
- Generate setpoint recommendations (supply air temp, chilled water setpoint)
- Propose chiller sequencing (lead/lag assignment based on load percentage)
- Identify load-shifting opportunities (pre-cool before tariff peak windows)
- Score maintenance urgency (0–100) per equipment fault
- Validate all recommendations against safety constraints (temp range, equipment limits)
- Output: ranked `recommendations` list in JSON with rationale

**Tools:**
```python
@tool("Setpoint Optimizer")
def optimize_setpoints(analyzer_output: dict, ambient_temp: float) -> dict: ...

@tool("Chiller Sequencer")
def recommend_chiller_sequencing(load_pct: float, num_chillers: int) -> dict: ...

@tool("Load Shift Planner")
def plan_load_shifting(forecast_df: pd.DataFrame, tariff_schedule: dict) -> list: ...

@tool("Maintenance Scorer")
def score_maintenance_priority(anomaly_report: dict) -> list: ...

@tool("ChromaDB Memory Query")
def query_past_recommendations(query_text: str) -> list: ...
```

---

### Agent 5 — Decision Report & Communication Agent

```
Role       : Technical Report Writer
Goal       : Produce a clear, complete, and actionable technical decision report
Backstory  : Engineering documentation specialist who translates AI outputs into operational clarity
```

**Responsibilities:**
- Consolidate outputs from Agents 1–4 into a unified data dict
- Render Jinja2 HTML template with all charts (Plotly → base64)
- Convert HTML to PDF using WeasyPrint
- Write both files to `reports/` directory
- Log report path and summary to SQLite
- Optionally store report summary as ChromaDB embedding for future retrieval

**Report Sections:**
1. Executive Summary (auto-generated LLM summary of run)
2. Data Quality Scorecard
3. Efficiency Dashboard (iKW-TR trend, kWh vs. benchmark)
4. Anomaly Log (table with severity, root cause, timestamp)
5. Energy Forecast (24h + 7d charts with confidence bands)
6. Top 5 Recommendations (action + rationale + expected savings)
7. Maintenance Priority Matrix

---

## 3. Tool Architecture

```
agents/tools/
│
├── data_tools.py          # CSV loader, timestamp aligner, feature engineer
├── thermo_tools.py        # WBT derivation, iKW-TR calculator (Stull equation)
├── anomaly_tools.py       # Isolation Forest, Z-score, root cause classifier
├── forecast_tools.py      # Prophet wrapper, XGBoost wrapper, peak detector
├── weather_tools.py       # Open-Meteo API client
├── optimization_tools.py  # Setpoint optimizer, sequencer, load-shift planner
├── report_tools.py        # Jinja2 renderer, Plotly chart generator, WeasyPrint PDF
└── memory_tools.py        # ChromaDB read/write wrappers
```

Each tool follows this signature pattern:
```python
from crewai.tools import tool

@tool("Tool Name")
def tool_function(input_param: str) -> str:
    """
    One-line description of what this tool does.
    Input: description of input format
    Output: description of output format
    """
    # implementation
    return json.dumps(result)
```

---

## 4. API Design

### Base URL: `http://localhost:8000/api/v1`

#### POST `/pipeline/run`
```json
Request:
{
  "dataset_path": "data/raw/chilledwater.csv",
  "weather_path": "data/raw/weather.csv",
  "building_id": "building_001",
  "forecast_horizon_hours": 24,
  "lat": 13.08,
  "lon": 80.27
}

Response:
{
  "run_id": "run_20260318_143022",
  "status": "queued",
  "estimated_duration_s": 180,
  "poll_url": "/api/v1/pipeline/status/run_20260318_143022"
}
```

#### GET `/pipeline/status/{run_id}`
```json
Response:
{
  "run_id": "run_20260318_143022",
  "status": "running",        // queued | running | completed | failed
  "current_agent": "Agent 3: Forecasting",
  "progress_pct": 60,
  "agents_completed": ["Ingestion", "Analysis"],
  "agents_pending": ["Forecasting", "Optimization", "Reporting"]
}
```

#### GET `/reports/{run_id}`
```json
Response:
{
  "run_id": "run_20260318_143022",
  "pdf_path": "reports/pdf/run_20260318_143022.pdf",
  "html_path": "reports/html/run_20260318_143022.html",
  "html_content": "<html>...</html>",   // inline for Electron viewer
  "generated_at": "2026-03-18T14:35:00Z",
  "summary": {
    "total_anomalies": 7,
    "avg_ikwtr": 0.72,
    "benchmark_ikwtr": 0.60,
    "top_recommendation": "Reduce chilled water setpoint by 1°C during 14:00–17:00"
  }
}
```

---

## 5. Data Flow

```
[Raw CSVs]
    │
    ▼
[Agent 1: Ingestion]
    │  clean_df (Parquet cached)
    ▼
[Agent 2: Analysis]
    │  anomaly_report.json
    │  efficiency_metrics.json
    ▼
[Agent 3: Forecasting]
    │  (also pulls weather from Open-Meteo API)
    │  forecast_24h.json
    │  forecast_168h.json
    │  peak_windows.json
    ▼
[Agent 4: Optimization]
    │  (also queries ChromaDB for past recommendations)
    │  recommendations.json  [ranked list, 5–10 actions]
    ▼
[Agent 5: Reporting]
    │  Merges all JSON outputs
    │  Renders Jinja2 template
    │  Generates Plotly charts → base64
    │  WeasyPrint: HTML → PDF
    ▼
[SQLite: run log + summary]
[File System: /reports/pdf/ + /reports/html/]
[ChromaDB: report embedding stored]
    │
    ▼
[FastAPI: report served to Electron]
    │
    ▼
[Electron: renders HTML inline, PDF download available]
```

---

## 6. Error Handling Strategy

### Agent-Level Errors

| Error Type | Strategy | Fallback |
|------------|----------|----------|
| Missing CSV column | Raise `DataValidationError`, halt Agent 1 | Log missing columns, use partial data if > 80% complete |
| iKW-TR derivation fails (zero tonnage) | Skip rows, flag in quality report | Estimate from historical average |
| Isolation Forest < 50 samples | Warn, use Z-score only | Log: "insufficient data for Isolation Forest" |
| Prophet training fails | Log exception, activate XGBoost fallback | XGBoost with engineered time features |
| Open-Meteo API timeout | Retry 3x with exponential backoff | Use last known weather data |
| WeasyPrint PDF fail | Log error, serve HTML-only report | Notify Electron: "PDF unavailable, HTML ready" |

### Pipeline-Level Error Handling

```python
# Each agent task wrapped in try/except
class AgentExecutionError(Exception):
    def __init__(self, agent_name: str, step: str, detail: str):
        self.agent_name = agent_name
        self.step = step
        self.detail = detail

# FastAPI endpoint catches and logs
@app.post("/api/v1/pipeline/run")
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    run_id = generate_run_id()
    background_tasks.add_task(execute_pipeline_safe, run_id, request)
    return {"run_id": run_id, "status": "queued"}

async def execute_pipeline_safe(run_id: str, request: PipelineRequest):
    try:
        result = crew.kickoff(inputs=request.dict())
        db.update_run_status(run_id, "completed")
    except AgentExecutionError as e:
        db.update_run_status(run_id, "failed", error=str(e))
        logger.error(f"[{run_id}] Agent {e.agent_name} failed at {e.step}: {e.detail}")
```

### Data Quality Thresholds

```python
QUALITY_THRESHOLDS = {
    "max_missing_pct": 15.0,       # Halt if > 15% missing in any core column
    "min_rows_for_ml": 48,         # Min rows for ML models (48h = 2 days hourly)
    "ikwtr_valid_range": (0.3, 2.0), # Flag if iKW-TR outside this range
    "temp_valid_range_c": (-10, 55),  # Ambient temp sanity check
}
```

---

## 7. Project Folder Structure

```
hvac-multiagent-system/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings, env vars
│   ├── database.py                # SQLAlchemy models + session
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── crew.py                # CrewAI Crew definition
│   │   ├── agent_definitions.py   # All 5 Agent objects
│   │   ├── task_definitions.py    # All 5 Task objects
│   │   └── tools/
│   │       ├── data_tools.py
│   │       ├── thermo_tools.py
│   │       ├── anomaly_tools.py
│   │       ├── forecast_tools.py
│   │       ├── weather_tools.py
│   │       ├── optimization_tools.py
│   │       ├── report_tools.py
│   │       └── memory_tools.py
│   │
│   ├── routers/
│   │   ├── pipeline.py
│   │   ├── reports.py
│   │   └── data.py
│   │
│   └── templates/
│       └── report_template.html   # Jinja2 HTML report template
│
├── frontend/
│   ├── package.json
│   ├── main.js                    # Electron main process
│   ├── preload.js
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── Dashboard.jsx
│       │   ├── UploadPanel.jsx
│       │   └── ReportViewer.jsx
│       └── index.html
│
├── data/
│   ├── raw/                       # Original CSVs (gitignored)
│   └── processed/                 # Cleaned datasets (gitignored)
│
├── reports/
│   ├── pdf/                       # Generated PDF reports
│   └── html/                      # Generated HTML reports
│
├── models/
│   └── saved/                     # Serialized ML models
│
└── tests/
    ├── test_data_tools.py
    ├── test_thermo_tools.py
    ├── test_anomaly_tools.py
    ├── test_forecast_tools.py
    ├── test_optimization_tools.py
    ├── test_pipeline_api.py
    └── fixtures/
        └── sample_data.csv        # Small test fixture (100 rows)
```

---

## 8. Scalability Considerations

### Current Scale (Resume Project)
- 1–3 buildings, 30–365 days, hourly data
- SQLite, single-process FastAPI, local Electron
- Adequate for demo and portfolio purposes

### Scale-Up Path (When Needed)

| Concern | Current | Scale-Up Solution |
|---------|---------|-------------------|
| Multiple buildings simultaneously | Sequential | Celery task queue + Redis broker |
| Large datasets (> 5 years) | In-memory Pandas | Dask DataFrames or chunked processing |
| Database | SQLite | PostgreSQL + connection pooling |
| Forecasting | Single Prophet | Model-per-building with versioning |
| Report storage | Local files | S3-compatible object storage |
| Deployment | Local only | Docker Compose (backend + frontend) |

### Stateless Agent Design
Each agent only depends on its input data and its own tools — no shared mutable state. This makes horizontal scaling (running multiple pipelines in parallel) straightforward: each pipeline run is an isolated CrewAI `Crew.kickoff()` call with its own `run_id`.
