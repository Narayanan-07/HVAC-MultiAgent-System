# Product Requirements Document (PRD)
## Multi-Agent HVAC Optimization System
**Version:** 1.0.0 | **Status:** Active Development | **Author:** Senior PM

---

## 1. Problem Statement

Energy systems in commercial buildings (hotels, malls, office spaces) generate massive volumes of operational data every minute — kWh readings, chiller efficiency metrics, ambient conditions, and occupancy load profiles. Despite this data richness, facility managers operate reactively: they respond to failures after they occur, rely on manual spreadsheet analysis, and lack the tools to convert raw sensor data into timely, explainable decisions.

The core gap is not data availability — it is **intelligence**. There is no system that autonomously ingests multi-parameter HVAC data, detects inefficiencies in real time, forecasts future demand, and delivers precise technical recommendations with engineering rationale.

This project builds that system.

---

## 2. Objectives

| # | Objective | Measurable Outcome |
|---|-----------|-------------------|
| O1 | Automate HVAC data ingestion and preprocessing | Clean dataset ready in < 30s for 30-day batch |
| O2 | Detect performance inefficiencies and anomalies | Anomaly detection with root-cause classification |
| O3 | Forecast 24–168 hour energy demand | MAPE < 10% on test set |
| O4 | Generate actionable optimization recommendations | Setpoint, sequencing, load-shifting actions with rationale |
| O5 | Produce automated technical decision reports | PDF/HTML report generated per analysis cycle |
| O6 | Deliver explainable AI decisions | Every recommendation includes technical justification |

---

## 3. System Scope

### 3.1 In Scope
- Processing 4 core parameters: **kWh**, **iKW-TR**, **Ambient Conditions** (Temp, Humidity, WBT), **Load Profiles**
- Multi-agent pipeline: Ingestion → Analysis → Forecasting → Optimization → Reporting
- BDG2 + Kaggle Chiller Energy datasets as primary data sources
- iKW-TR derivation from raw power and tonnage columns
- Automated PDF/HTML decision report generation
- FastAPI backend with Electron desktop frontend
- SQLite for development, PostgreSQL-ready for production
- Optional: Conversational interface (English/Tamil) via CrewAI

### 3.2 Out of Scope
- Real-time hardware sensor integration (Phase 1)
- Docker/cloud deployment (resume project scope)
- Mobile application
- BACnet/Modbus protocol integration

---

## 4. Core Parameters

### Parameter 1 — kWh (Total Energy Consumption)
- Source: BDG2 `chilledwater.csv`, `electricity.csv`
- Granularity: Hourly
- Derived metric: Daily/weekly aggregates, peak demand (kW)

### Parameter 2 — iKW-TR (Instantaneous kW per Ton of Refrigeration)
- **Not directly available in public datasets — derived as:**
  ```
  iKW-TR = Total Chiller Power (kW) / Cooling Load (Tons of Refrigeration)
  Cooling Load (TR) = Flow (m³/s) × ΔT × 4187 / 3517
  ```
- Industry benchmark: Good chiller = 0.5–0.65 kW/TR | Poor = > 0.8 kW/TR
- Used by Agent 2 (Performance Analyzer) for efficiency benchmarking

### Parameter 3 — Ambient Conditions
- Columns: `air_temperature` (°C), `relative_humidity` (%), `dew_temperature` (°C)
- WBT derived using Stull equation from dry-bulb temp + relative humidity
- Source: BDG2 `weather.csv` (site-level hourly data)

### Parameter 4 — Load Profiles
- Occupancy patterns inferred from energy signatures (hourly kWh shape)
- Equipment usage from chiller percent load and meter type breakdown
- Demand patterns: peak/off-peak classification, weekday/weekend/holiday tagging

---

## 5. Functional Requirements

### FR-01: Data Ingestion Agent
- SHALL ingest CSV files from BDG2 and Kaggle Chiller datasets
- SHALL validate completeness, detect missing values, and apply imputation
- SHALL normalize timestamps to UTC and align multi-source data by timestamp
- SHALL engineer features: WBT derivation, iKW-TR calculation, rolling averages
- SHALL output a clean, unified dataframe to all downstream agents

### FR-02: Performance Analyzer Agent
- SHALL compute actual iKW-TR vs. design benchmark (0.6 kW/TR baseline)
- SHALL detect anomalies using Isolation Forest + Z-score methods
- SHALL classify root causes as: weather-driven | equipment-driven | behavioral
- SHALL quantify severity (Low / Medium / High / Critical) and duration
- SHALL flag chiller degradation trends over 7–30 day windows

### FR-03: Forecasting Agent
- SHALL generate 24-hour and 168-hour (7-day) energy load forecasts
- SHALL incorporate weather forecast adjustment (temperature/humidity impact)
- SHALL predict peak demand periods (15-min resolution for next 24h)
- SHALL output confidence intervals (80% and 95%) with every forecast
- SHALL use LSTM or Prophet as primary model, XGBoost as fallback

### FR-04: Optimization & Recommendation Agent
- SHALL recommend HVAC setpoint adjustments with expected kWh savings
- SHALL propose chiller sequencing (which chiller to lead/lag based on load)
- SHALL suggest pre-cooling or load-shifting windows to avoid peak tariffs
- SHALL score maintenance urgency (0–100) for each detected fault
- SHALL output recommendations in structured JSON with rationale text

### FR-05: Decision Report Agent
- SHALL consolidate outputs from all agents into a single technical report
- SHALL generate report in both PDF and HTML formats
- SHALL include: executive summary, efficiency scorecard, anomaly log, forecast charts, top-5 recommendations
- SHALL produce report within 60 seconds of analysis completion
- SHALL embed charts/graphs as base64 in HTML report

### FR-06: API Layer (FastAPI)
- SHALL expose REST endpoints for each agent trigger
- SHALL provide `/run-pipeline` endpoint for full analysis cycle
- SHALL return structured JSON responses with timestamps and run IDs
- SHALL persist all run results to SQLite database

### FR-07: Frontend (Electron)
- SHALL display real-time analysis status per agent
- SHALL render HTML report inline
- SHALL allow CSV file upload for new dataset analysis
- SHALL show historical run logs

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Full pipeline (5 agents) completes in < 5 minutes for 30-day dataset |
| **Reliability** | System must handle missing data up to 15% without crashing |
| **Explainability** | Every recommendation must include minimum 2-sentence technical rationale |
| **Accuracy** | Forecast MAPE ≤ 10%, Anomaly Precision ≥ 85% |
| **Maintainability** | Each agent is independently replaceable/upgradeable |
| **Code Quality** | Type hints, docstrings, unit tests per module (pytest) |
| **Data Integrity** | All raw data preserved; derived columns are clearly labeled |
| **Portability** | Runs on Windows/macOS/Linux (Electron + Python cross-platform) |

---

## 7. User Personas

### Persona 1 — Facility Manager (Primary User)
- **Name:** Rajan, 45, manages 3-star hotel in Chennai
- **Goal:** Reduce monthly electricity bill, avoid chiller breakdowns
- **Pain:** No time for data analysis; gets monthly reports that are already outdated
- **Needs:** Daily automated alerts, simple green/yellow/red status, clear "do this today" actions

### Persona 2 — HVAC Engineer (Power User)
- **Name:** Divya, 32, MEP consultant for commercial buildings
- **Goal:** Benchmark chiller performance across buildings, justify capex
- **Pain:** Manual data collection across sites is time-consuming
- **Needs:** iKW-TR trend charts, chiller COP history, technical PDF reports for clients

### Persona 3 — Energy Auditor (Analyst)
- **Name:** Arjun, 28, certified energy auditor
- **Goal:** Identify energy waste, calculate potential savings
- **Pain:** AI systems give outputs without reasoning — hard to defend to clients
- **Needs:** Explainable decisions with data references, anomaly root-cause logs

---

## 8. Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Pipeline execution time | < 5 min (30-day data) | Automated timer in logs |
| Forecast accuracy (MAPE) | ≤ 10% | Hold-out test set validation |
| Anomaly detection precision | ≥ 85% | Labeled fault data cross-validation |
| iKW-TR derivation accuracy | ± 2% vs. manual calculation | Engineering spot-check |
| Report generation time | < 60 seconds | End-to-end test |
| Recommendations per run | ≥ 5 actionable items | Report audit |
| Code test coverage | ≥ 70% | pytest-cov report |
