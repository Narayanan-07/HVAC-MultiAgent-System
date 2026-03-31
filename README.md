# Multi-Agent HVAC Optimization System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![CrewAI](https://img.shields.io/badge/CrewAI-1.9.3-orange?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=for-the-badge&logo=fastapi)
![Electron](https://img.shields.io/badge/Electron-29-blue?style=for-the-badge&logo=electron)
![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-purple?style=for-the-badge&logo=google)

**A production-grade, local-first multi-agent AI system that autonomously converts raw HVAC building energy data into explainable operational decisions and automated technical reports.**

[Features](#features) • [Architecture](#architecture) • [Agents](#agents) • [Dataset](#dataset) • [Quickstart](#quickstart) • [API](#api-reference) • [System Differentiation](#system-differentiation)

</div>

---

## Problem Statement

Commercial building HVAC systems consume nearly **40% of total building energy**, yet facility managers lack intelligent tools to convert raw operational data into timely, explainable decisions. Existing AI approaches rely on simulation environments, operate on single buildings, produce black-box decisions, and fail to deliver actionable technical reports to human operators — creating a critical gap between AI research and real-world facility management.

---

## Features

- **5-Agent CrewAI Pipeline** — Sequential multi-agent orchestration: Ingest → Analyze → Forecast → Optimize → Report.
- **Real Multi-Building Data** — Processes BDG2 dataset: 307 commercial buildings, 5.2M rows, 2016–2017 hourly.
- **4 Core HVAC Parameters** — kWh consumption, iKW-TR efficiency metric, ambient conditions (Temp/Humidity/WBT), load profiles.
- **Anomaly Detection** — Isolation Forest + Z-Score with root cause classification (weather/equipment/behavioral).
- **Energy Forecasting** — Prophet (primary) + XGBoost (fallback), 24h and 168h horizons with confidence intervals.
- **Explainable Recommendations** — Every optimization action includes a technical rationale.
- **Automated Reports** — PDF + HTML decision reports with Plotly charts, generated per analysis run.
- **Desktop Interface** — Electron app with dark SaaS-style dashboard, report viewer, and analysis history.

---

## Previews

*(Replace the placeholder links below with your actual project screenshots or GIFs)*

<p align="center">
  <img src="docs/placeholder-dashboard.png" width="48%" alt="Dashboard Overview">
  <img src="docs/placeholder-report.png" width="48%" alt="Generated PDF Report">
</p>

---

## Architecture

```text
=======================================================================
                    ELECTRON DESKTOP APP                      
   Dashboard | Report Viewer | Analysis History               
=======================================================================
                       | HTTP REST (localhost:8000)
=======================v===============================================
                    FASTAPI BACKEND                           
   POST /pipeline/run | GET /pipeline/status | GET /reports   
=======================v===============================================
                       |
=======================v===============================================
                 CREWAI AGENT PIPELINE                        
                                                              
  [ Agent 1 ]  [ Agent 2 ]  [ Agent 3 ]  [ Agent 4 ]    
  [ Ingest  ]->[ Analyze ]->[ Forecast]->[ Optimize].. 
                                                 |           
                                          [ Agent 5 ]      
                                          [  Report ]      
=======================================================================
              |                    |                |
        [ SQLite DB ]      [ ChromaDB ]     [ File System ]
                                   ^
                           [ Open-Meteo API ]
```

> See `docs/HVAC Architecture.png` for the full visual architecture diagram.

---

## Agents

| # | Agent | Role | Key Capabilities |
|---|-------|------|-----------------|
| 1 | **Data Ingestion** | Data Engineer | Load & melt wide CSVs, derive iKW-TR, derive RH + WBT (Stull equation), feature engineering, quality report |
| 2 | **Performance Analyzer** | HVAC Diagnostician | Isolation Forest anomaly detection, Z-Score validation, root cause classification (weather/equipment/behavioral), degradation trend scoring |
| 3 | **Forecasting** | Energy Forecaster | Prophet 24h/168h forecasting, XGBoost fallback, weather-adjusted predictions, peak demand window detection, confidence intervals |
| 4 | **Optimizer** | HVAC Consultant | Setpoint recommendations, chiller sequencing logic, load-shift planning, maintenance priority scoring (0–100) |
| 5 | **Report Generator** | Technical Writer | Jinja2 HTML template, Plotly chart generation (trend, heatmap, forecast), pdfkit PDF export, executive summary |

---

## Dataset

This system uses the **[Building Data Genome Project 2 (BDG2)](https://github.com/buds-lab/building-data-genome-project-2)** — a real-world open dataset of commercial building energy consumption.

| Property | Value |
|----------|-------|
| Buildings | 307 (lodging, office, retail) |
| Time Range | 2016–2017 (2 full years) |
| Granularity | Hourly |
| Total Rows | ~5.2 million |
| Sites | Multiple (Panther, Fox, Eagle, Hog, Bull, etc.) |

**Files needed:**
```text
data/raw/
├── chilledwater.csv     # Chilled water meter readings (kWh) — wide format
├── electricity.csv      # Electricity consumption (kWh) — wide format
├── weather.csv          # Hourly weather per site (temp, dewpoint, wind)
└── metadata.csv         # Building info (type, size, lat/lng)
```

**Core parameters derived:**

| Parameter | Source | Formula |
|-----------|--------|---------|
| `kWh` | electricity.csv | Direct meter reading |
| `iKW-TR` | Both CSVs | `electricity_kW / (chilledwater_kWh * 0.9699)` |
| `Ambient Conditions` | weather.csv | airTemp, dewTemp → RH (Magnus), WBT (Stull 2011) |
| `Load Profiles` | electricity.csv | Rolling avg, percentile categorization, day patterns |

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- [wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) (for PDF generation)
- [Gemini API Key](https://aistudio.google.com) (free tier)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/hvac-multiagent-system.git
cd hvac-multiagent-system

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_key_here
DATABASE_URL=sqlite:///./hvac_system.db
REPORTS_DIR=reports
DATA_DIR=data
LOG_LEVEL=INFO
```

### 3. Prepare Dataset

Download BDG2 from [GitHub](https://github.com/buds-lab/building-data-genome-project-2) and place the 4 CSVs in `data/raw/`.

Then run the data preparation pipeline:
```bash
python scripts/prepare_data.py
```

### 4. Start Backend

```bash
uvicorn backend.main:app --port 8000
```

Verify status by navigating to `http://localhost:8000/health`.

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev        # React dev server
npx electron .     # Electron desktop window
```

### 6. Run Analysis

Open the Electron app -> Dashboard -> Upload CSVs -> Enter building ID -> Click **Run Analysis**

---

## Testing

Generate test fixtures first:
```bash
python tests/fixtures/generate_fixtures.py
```

Run full test suite:
```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
```

| Module | Coverage |
|--------|----------|
| anomaly_tools.py | 72% |
| forecast_tools.py | 84% |
| data_tools.py | 63% |
| optimization_tools.py | 54% |
| report_tools.py | 72% |

---

## API Reference

### Base URL: `http://localhost:8000/api/v1`

| Endpoint | Method | Description | Request Body |
|----------|--------|-------------|-------------|
| `/pipeline/run` | POST | Trigger full 5-agent pipeline | `{building_id, dataset_path, forecast_horizon_hours, lat, lon}` |
| `/pipeline/status/{run_id}` | GET | Poll pipeline execution status | None |
| `/reports/{run_id}` | GET | Get HTML report + metadata | None |
| `/reports/{run_id}/pdf` | GET | Download PDF report | None |
| `/history` | GET | Last 20 pipeline runs | None |
| `/health` | GET | Health check | None |

---

## System Differentiation 

This platform directly bridges the gap between academic HVAC research and practical industry application. It explicitly targets limitations identified in modern systematic reviews (e.g., *Aghili et al., "Artificial Intelligence Approaches to Energy Management in HVAC Systems", Buildings 2025*):

| Common Industry Limitation | System Approach |
|---|---|
| Black-box AI without explainability | Every recommendation includes a technical rationale for operators |
| Systems bound to simulated datasets | Validated entirely on the real-world BDG2 dataset (307 buildings) |
| Lacking facility manager interfaces | Includes a dedicated Electron desktop app tailored for non-technical users |
| Missing automated documentation | Generates completely standalone PDF and HTML decision reports per run |
| Pure algorithmic logic without deduction | Utilizes an LLM multi-agent orchestration pattern (CrewAI + Gemini) |

This architecture proves that multi-agent systems can handle end-to-end data ingestion, algorithmic forecasting, and explainable reporting locally without relying heavily on cloud infrastructure.

---

## Challenges & Learnings

- **Agent Hallucinations in Technical Output:** Initially, agents would hallucinate HVAC parameters. This was resolved by equipping them with rigid tools to execute deterministically (e.g., Python-based Isolation Forests and Prophet algorithms), utilizing the LLM exclusively for orchestration and reasoning layer tasks rather than raw math.
- **Handling High-Dimensional Time-Series:** Processing 5.2 million rows of wide-format data efficiently required shifting away from naive pandas loading to optimized melting and chunking strategies before handing aggregates to agents.
- **Bridging Asynchronous AI with UI State:** Long-running CrewAI pipelines (taking minutes) made generic HTTP request patterns timeout. I implemented an asynchronous queue and polling mechanism with SQLite state tracking so the Electron UI remained perfectly responsive during the run.

---

## Project Structure

```text
hvac-multiagent-system/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings
│   ├── database.py                # SQLAlchemy models
│   ├── pipeline.py                # Async pipeline runner
│   ├── agents/
│   │   ├── agent_definitions.py   # All 5 CrewAI agents
│   │   ├── task_definitions.py    # All 5 CrewAI tasks
│   │   ├── crew.py                # Crew assembly
│   │   └── tools/                 # Agent tools
│   ├── routers/                   # API routes
│   └── templates/                 # Report Jinja2 templates
├── frontend/                      # Electron + React app
├── data/                          # BDG2 datasets (raw & processed)
├── reports/                       # Generated PDFs & HTML reports
├── tests/                         # pytest suite
└── scripts/                       # Data prep utilities
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Multi-Agent Framework** | CrewAI |
| **LLM** | Google Gemini 2.0 Flash |
| **Backend API** | FastAPI + Uvicorn |
| **Machine Learning** | Scikit-learn, Prophet, XGBoost |
| **Memory / Database** | ChromaDB, SQLite |
| **Data Processing** | Pandas, NumPy |
| **Desktop / Frontend** | Electron, React 18, TailwindCSS |

---

## Acknowledgements

- Building Data Genome Project 2 — Miller et al., for the open dataset.
- CrewAI — Framework for multi-agent logic.
- Open-Meteo — Open source weather API.

<div align="center">
Built as a production-grade AI engineering portfolio project
</div>