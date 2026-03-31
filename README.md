# 🏢 Multi-Agent HVAC Optimization System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![CrewAI](https://img.shields.io/badge/CrewAI-1.9.3-orange?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=for-the-badge&logo=fastapi)
![Electron](https://img.shields.io/badge/Electron-29-blue?style=for-the-badge&logo=electron)
![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-purple?style=for-the-badge&logo=google)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A production-grade, local-first multi-agent AI system that autonomously converts raw HVAC building energy data into explainable operational decisions and automated technical reports.**

[Features](#features) • [Architecture](#architecture) • [Agents](#agents) • [Dataset](#dataset) • [Quickstart](#quickstart) • [API](#api-reference) • [Research](#research-novelty)

</div>

---

## 🎯 Problem Statement

Commercial building HVAC systems consume nearly **40% of total building energy**, yet facility managers lack intelligent tools to convert raw operational data into timely, explainable decisions. Existing AI approaches rely on simulation environments, operate on single buildings, produce black-box decisions, and fail to deliver actionable technical reports to human operators — creating a critical gap between AI research and real-world facility management.

---

## ✨ Features

- **5-Agent CrewAI Pipeline** — Sequential multi-agent orchestration: Ingest → Analyze → Forecast → Optimize → Report
- **Real Multi-Building Data** — Processes BDG2 dataset: 307 commercial buildings, 5.2M rows, 2016–2017 hourly
- **4 Core HVAC Parameters** — kWh consumption, iKW-TR efficiency metric, ambient conditions (Temp/Humidity/WBT), load profiles
- **Anomaly Detection** — Isolation Forest + Z-Score with root cause classification (weather/equipment/behavioral)
- **Energy Forecasting** — Prophet (primary) + XGBoost (fallback), 24h and 168h horizons with confidence intervals
- **Explainable Recommendations** — Every optimization action includes a technical rationale
- **Automated Reports** — PDF + HTML decision reports with Plotly charts, generated per analysis run
- **Desktop Interface** — Electron app with dark SaaS-style dashboard, report viewer, and history

---

## 🏗️ Architecture

```
╔══════════════════════════════════════════════════════════════╗
║                    ELECTRON DESKTOP APP                      ║
║   Dashboard │ Report Viewer │ Analysis History               ║
╚══════════════════════╤═══════════════════════════════════════╝
                       │ HTTP REST (localhost:8000)
╔══════════════════════▼═══════════════════════════════════════╗
║                    FASTAPI BACKEND                           ║
║   POST /pipeline/run │ GET /pipeline/status │ GET /reports   ║
╚══════════════════════╤═══════════════════════════════════════╝
                       │
╔══════════════════════▼═══════════════════════════════════════╗
║                 CREWAI AGENT PIPELINE                        ║
║                                                              ║
║  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    ║
║  │ Agent 1  │→ │ Agent 2  │→ │ Agent 3  │→ │ Agent 4  │→.. ║
║  │ Ingest   │  │ Analyze  │  │ Forecast │  │ Optimize │    ║
║  └──────────┘  └──────────┘  └──────────┘  └──────────┘    ║
║                                                  ↓           ║
║                                           ┌──────────┐      ║
║                                           │ Agent 5  │      ║
║                                           │  Report  │      ║
║                                           └──────────┘      ║
╚═════════════╤════════════════════╤════════════════╤══════════╝
              ↓                    ↓                ↓
        ┌──────────┐        ┌──────────┐    ┌──────────┐
        │  SQLite  │        │ ChromaDB │    │   File   │
        │    DB    │        │  Memory  │    │  System  │
        └──────────┘        └──────────┘    └──────────┘
                                    ↑
                            ┌──────────────┐
                            │ Open-Meteo   │
                            │ Weather API  │
                            └──────────────┘
```

> 📐 See `docs/HVAC Architecture.png` for the full visual architecture diagram.

---

## 🤖 Agents

| # | Agent | Role | Key Capabilities |
|---|-------|------|-----------------|
| 1 | **Data Ingestion** | Data Engineer | Load & melt wide CSVs, derive iKW-TR, derive RH + WBT (Stull equation), feature engineering, quality report |
| 2 | **Performance Analyzer** | HVAC Diagnostician | Isolation Forest anomaly detection, Z-Score validation, root cause classification (weather/equipment/behavioral), degradation trend scoring |
| 3 | **Forecasting** | Energy Forecaster | Prophet 24h/168h forecasting, XGBoost fallback, weather-adjusted predictions, peak demand window detection, confidence intervals |
| 4 | **Optimizer** | HVAC Consultant | Setpoint recommendations, chiller sequencing logic, load-shift planning, maintenance priority scoring (0–100) |
| 5 | **Report Generator** | Technical Writer | Jinja2 HTML template, Plotly chart generation (trend, heatmap, forecast), pdfkit PDF export, executive summary |

---

## 📊 Dataset

This system uses the **[Building Data Genome Project 2 (BDG2)](https://github.com/buds-lab/building-data-genome-project-2)** — a real-world open dataset of commercial building energy consumption.

| Property | Value |
|----------|-------|
| Buildings | 307 (lodging, office, retail) |
| Time Range | 2016–2017 (2 full years) |
| Granularity | Hourly |
| Total Rows | ~5.2 million |
| Sites | Multiple (Panther, Fox, Eagle, Hog, Bull, etc.) |

**Files needed:**
```
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
| `iKW-TR` | Both CSVs | `electricity_kW / (chilledwater_kWh × 0.9699)` |
| `Ambient Conditions` | weather.csv | airTemp, dewTemp → RH (Magnus), WBT (Stull 2011) |
| `Load Profiles` | electricity.csv | Rolling avg, percentile categorization, day patterns |

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- [wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) (for PDF generation — Windows 64-bit)
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
```
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

Expected output:
```
Data quality score: 83.1 — PASS
307 buildings | 5.2M rows | 2016-2017
features_final.csv saved to data/processed/
```

### 4. Start Backend

```bash
uvicorn backend.main:app --port 8000
```

Verify: `http://localhost:8000/health` → `{"status": "ok", "version": "1.0.0"}`

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev        # React dev server (port 3000)
npx electron .     # Electron desktop window
```

### 6. Run Analysis

Open the Electron app → Dashboard → Upload CSVs → Enter building ID → Click **Run Analysis**

---

## 🧪 Testing

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

## 🌐 API Reference

### Base URL: `http://localhost:8000/api/v1`

| Endpoint | Method | Description | Request Body |
|----------|--------|-------------|-------------|
| `/pipeline/run` | POST | Trigger full 5-agent pipeline | `{building_id, dataset_path, forecast_horizon_hours, lat, lon}` |
| `/pipeline/status/{run_id}` | GET | Poll pipeline execution status | — |
| `/reports/{run_id}` | GET | Get HTML report + metadata | — |
| `/reports/{run_id}/pdf` | GET | Download PDF report | — |
| `/data/upload` | POST | Upload CSV dataset | `multipart/form-data` |
| `/history` | GET | Last 20 pipeline runs | — |
| `/health` | GET | Health check | — |

**Example — Trigger Pipeline:**
```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"building_id": "Eagle_office_Amanda", "dataset_path": "data/processed/features_final.csv", "forecast_horizon_hours": 24, "lat": 13.08, "lon": 80.27}'
```

**Response:**
```json
{"run_id": "run_20260331_143022", "status": "queued"}
```

---

## 🔬 Research Novelty

This project directly addresses **5 limitations** explicitly identified in the 2025 systematic review:

> *Aghili et al., "Artificial Intelligence Approaches to Energy Management in HVAC Systems: A Systematic Review", Buildings 2025, 15, 1008*

| Gap in Literature | This System |
|---|---|
| ❌ Black-box AI — no explainability | ✅ Every recommendation includes technical rationale |
| ❌ Simulated/synthetic data only | ✅ Real BDG2 dataset — 307 buildings, 5.2M rows |
| ❌ Single building, single zone | ✅ Multi-building: lodging, office, retail |
| ❌ No automated report for operators | ✅ Auto PDF + HTML decision report per run |
| ❌ No LLM-based orchestration | ✅ CrewAI + Gemini 2.0 Flash multi-agent pipeline |
| ❌ iKW-TR not used as metric | ✅ iKW-TR derived and used as core efficiency metric |
| ❌ No end-to-end pipeline | ✅ Raw CSV → Analysis → Forecast → Optimize → Report |
| ❌ No facility manager interface | ✅ Electron desktop app for non-technical users |

**Novelty Statement:**

> *This is the first LLM-orchestrated multi-agent architecture (CrewAI + Gemini) that combines anomaly detection, energy forecasting, HVAC optimization, and explainable automated report generation for commercial buildings using real multi-building operational data — without requiring simulation environments, RL training, or cloud infrastructure.*

---

## 📁 Project Structure

```
hvac-multiagent-system/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings
│   ├── database.py                # SQLAlchemy models
│   ├── llm.py                     # Gemini LLM client
│   ├── pipeline.py                # Async pipeline runner
│   ├── data_pipeline.py           # Data preparation
│   ├── agents/
│   │   ├── agent_definitions.py   # All 5 CrewAI agents
│   │   ├── task_definitions.py    # All 5 CrewAI tasks
│   │   ├── crew.py                # Crew assembly
│   │   └── tools/                 # Agent tools
│   │       ├── data_tools.py
│   │       ├── anomaly_tools.py
│   │       ├── forecast_tools.py
│   │       ├── weather_tools.py
│   │       ├── optimization_tools.py
│   │       └── report_tools.py
│   ├── routers/
│   │   ├── pipeline.py
│   │   ├── reports.py
│   │   └── data.py
│   └── templates/
│       └── report_template.html
├── frontend/                      # Electron + React app
├── data/
│   ├── raw/                       # Input CSVs
│   └── processed/                 # Engineered features
├── reports/
│   ├── pdf/                       # Generated PDFs
│   └── html/                      # Generated HTML reports
├── tests/                         # pytest suite
├── scripts/
│   └── prepare_data.py            # Data preparation script
├── docs/
│   └── HVAC Architecture.png      # System architecture diagram
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Multi-Agent Framework | CrewAI | 1.9.3 |
| LLM | Google Gemini 2.0 Flash | — |
| Backend | FastAPI + Uvicorn | 0.110.0 |
| Data Processing | Pandas + NumPy | 2.2.3 |
| Anomaly Detection | Scikit-learn (IsolationForest) | 1.5.2 |
| Forecasting | Prophet + XGBoost | 1.1.5 / 2.1.3 |
| Vector Memory | ChromaDB | 1.1.0 |
| Report Generation | Jinja2 + pdfkit + Plotly | — |
| Database | SQLite (SQLAlchemy) | — |
| Desktop Frontend | Electron + React 18 | 29 |
| Styling | TailwindCSS | — |
| Testing | pytest + pytest-cov | — |

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Building Data Genome Project 2](https://github.com/buds-lab/building-data-genome-project-2) — Miller et al., for the open dataset
- [CrewAI](https://github.com/crewAIInc/crewAI) — Multi-agent framework
- [Open-Meteo](https://open-meteo.com) — Free weather forecast API
- Aghili et al. (2025) — Systematic review that informed the research gap analysis

---

<div align="center">
Built with ❤️ as a production-grade AI engineering portfolio project
</div>