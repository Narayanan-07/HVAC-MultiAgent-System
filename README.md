# Multi-Agent HVAC Optimization System

A local-first, multi-agent artificial intelligence system designed to automate the ingestion, analysis, forecasting, and optimization of building HVAC (Heating, Ventilation, and Air Conditioning) energy data. Powered by CrewAI, FastAPI, and Electron, it provides facility managers with actionable, explainable technical recommendations and PDF/HTML reports without requiring cloud connectivity.

---

## Architecture Diagram

```text
+-------------------------------------------------------------+
|                     ELECTRON FRONTEND                       |
|          (Desktop UI + HTML Report Viewer)                  |
+-----------------------------+-------------------------------+
                              | HTTP / REST
+-----------------------------v-------------------------------+
|                    FASTAPI BACKEND                          |
|                (Orchestration Layer)                        |
|   +-----------------------------------------------------+   |
|   |                 CREWAI AGENT LAYER                  |   |
|   |  [Agent 1] -> [Agent 2] -> [Agent 3] -> [Agent 4]   |   |
|   |   Ingest       Analyze      Forecast     Optimize   |   |
|   |                         |                           |   |
|   |                         v                           |   |
|   |                     [Agent 5]                       |   |
|   |                      Report                         |   |
|   +-----------------------------------------------------+   |
+-------------------+-------------------+---------------------+
                    |                   |
            +-------v------+     +------v------+
            |  SQLite DB   |     | File System |
            |  (Run Logs)  |     | CSV/Reports |
            +--------------+     +-------------+
```

---

## Tech Stack

- **Multi-Agent Framework**: CrewAI
- **Backend Orchestrator**: FastAPI (Python 3.13)
- **Frontend / Client**: Electron (React + TailwindCSS)
- **Data & ML**: Pandas, Scikit-learn (Isolation Forest), Meta Prophet, XGBoost
- **Storage**: SQLite Database (extendable to PostgreSQL)

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.13+
- Node.js (v18+)

### 2. Backend Setup
```bash
# Clone the repository and navigate to backend
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS/Linux

# Install requirements
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY

# Run FastAPI Server
uvicorn backend.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm start
```

### 4. Running Tests
The project uses `pytest` for rigorous testing >70% coverage.
```bash
pytest tests/
```

---

## Dataset Instructions

The system expects data styled after the [BDG2](https://github.com/buds-lab/building-data-genome-project-2) dataset. 
Place your CSVs into the `data/raw/` folder before running the pipeline or test suites.

- `features_final.csv`: The primary processed file containing at minimum `timestamp`, `building_id`, `chilledwater_kwh`, `electricity_kwh`, `airTemperature`, `relative_humidity`, and `iKW_TR`.

To generate mock data for testing:
```bash
python tests/fixtures/generate_fixtures.py
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/pipeline/run` | POST | Triggers the full 5-agent CrewAI pipeline. Returns a `run_id`. |
| `/api/v1/pipeline/status/{id}` | GET | Polls the current state of a pipeline run. |
| `/api/v1/reports/{run_id}` | GET | Returns the generated report metadata and paths (PDF/HTML). |
| `/api/v1/data/upload` | POST | Uploads raw CSV data into memory for subsequent pipeline runs. |

---

## Agent Descriptions

| Agent | Role | Tools & Capabilities |
|---|---|---|
| **Agent 1: Ingestion** | Engineer | CSV loading, timestamp alignment, Missing value interpolation, iKW/TR derivation. |
| **Agent 2: Analyzer** | Diagnostics | iKW/TR Benchmarking, Isolation Forest anomaly mapping, Root Cause Classification. |
| **Agent 3: Forecaster** | Data Science | Prophet & XGBoost time-series regression, Peak demand windows detection. |
| **Agent 4: Optimizer** | Consultant | Chiller sequencing, Temperature setpoint recommendations, load shifting scheduling. |
| **Agent 5: Reporter** | Communicator | Jinja2 HTML rendering, Plotly chart generation, WeasyPrint/PDFKit conversion. |

---

## Research Novelty

While commercial HVAC systems possess copious IoT metadata, this project introduces a fully localized Multi-Agent LLM architectural pipeline that interprets raw continuous numerical streams (`kWh`, `iKW/TR`, `weather`) mapping them intrinsically to **discrete, deterministic engineering strategies** with technical rationales, achieving diagnostic transparency without external cloud dependencies.

---

## License

MIT License.
