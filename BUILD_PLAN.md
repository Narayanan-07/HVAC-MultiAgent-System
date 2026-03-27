# HVAC Multi-Agent System — Phase-by-Phase Build Plan
## Complete Development Roadmap with AI Prompts & Test Methods
**For use with:** Claude / any LLM coding assistant

---

## 📋 How to Use This Document
1. Complete each phase **in order** — each builds on the previous
2. Each phase has: **What to build → AI Prompt → Test Method**
3. Copy the prompt exactly into your AI assistant
4. Run the test before moving to the next phase
5. Commit to GitHub at the end of each phase

---

## PHASE 0 — Project Setup & Repository Structure
**Duration:** 30 min | **Goal:** Working skeleton before any logic

### What to Build
- GitHub repo with correct folder structure
- Python virtual environment
- requirements.txt installed and verified
- .env file configured
- FastAPI server running (health check only)

### AI Prompt
```
Create the complete folder structure and boilerplate for a production-grade 
multi-agent HVAC optimization system with the following layout:

hvac-multiagent-system/
├── backend/
│   ├── main.py              (FastAPI app with /health endpoint only)
│   ├── config.py            (Pydantic BaseSettings, reads from .env)
│   ├── database.py          (SQLAlchemy setup, SQLite, create_all on startup)
│   ├── agents/
│   │   ├── __init__.py
│   │   └── tools/
│   │       └── __init__.py
│   └── routers/
│       └── __init__.py
├── frontend/                (empty for now)
├── data/raw/
├── data/processed/
├── reports/pdf/
├── reports/html/
├── models/saved/
├── tests/
│   └── fixtures/
├── requirements.txt         (use the exact list from Tech_Stack.md)
├── .env.example
└── .gitignore               (ignore .env, data/raw/, data/processed/, __pycache__)

Requirements:
- config.py must use pydantic-settings BaseSettings
- database.py must define a PipelineRun table with: run_id (str PK), 
  status (str), created_at (datetime), duration_s (float nullable)
- main.py must include lifespan context manager that calls create_all
- Add GET /health endpoint returning {"status": "ok", "version": "1.0.0"}
- Use loguru for all logging (not Python logging)
```

### Test Method
```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Start server
cd backend && uvicorn main:app --reload --port 8000

# 3. Check health
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0"}

# 4. Check Swagger UI
# Open browser: http://localhost:8000/docs
# Expected: Swagger page loads with /health endpoint visible

# 5. Check database created
ls -la backend/hvac_system.db
# Expected: file exists
```

---

## PHASE 1 — Data Ingestion & Preprocessing (Agent 1)
**Duration:** 2–3 hours | **Goal:** Clean dataframe with all 4 core parameters

### What to Build
- CSV loader for BDG2 format (chilledwater.csv + weather.csv + metadata.csv)
- Timestamp alignment and timezone normalization
- iKW-TR derivation function
- WBT derivation using Stull equation
- Feature engineering pipeline
- Data quality report generation
- Agent 1 definition in CrewAI

### AI Prompt
```
Build the complete Data Ingestion & Preprocessing module for a HVAC 
multi-agent system. Create these files:

1. backend/agents/tools/data_tools.py
   Functions (all as @tool decorated CrewAI tools):
   - load_bdg2_datasets(chilled_water_path, weather_path, metadata_path) -> str (JSON)
     * Loads 3 CSVs, validates required columns exist
     * Required columns: chilledwater.csv needs [timestamp, meter_reading]
       weather.csv needs [timestamp, air_temperature, relative_humidity, dew_temperature]
       metadata.csv needs [building_id, primary_use, square_feet]
     * Merges on timestamp (left join weather onto energy)
     * Returns JSON string of merged dataframe info
   
   - engineer_hvac_features(data_json: str) -> str (JSON)
     * Derives iKW-TR: (meter_reading_kw / cooling_tons) 
       where cooling_tons = meter_reading_kWh (chilled water meter IS cooling energy)
       iKW-TR = power_kw / (meter_reading_kWh * 3.517) -- convert kWh to TR-hours
     * Engineers: hour_of_day, day_of_week, is_weekend (bool), month
     * Creates rolling_avg_24h for meter_reading
     * Creates load_category: "low"/<33rd pct, "medium"/33-66th, "high"/>66th
     * Fills missing values: forward-fill up to 3 steps, then interpolate
     * Returns JSON with processed data stats

2. backend/agents/tools/thermo_tools.py
   Functions:
   - derive_wet_bulb_temperature(temp_c: float, relative_humidity_pct: float) -> float
     * Use Stull (2011) approximation formula:
       WBT = T * arctan(0.151977 * (RH + 8.313659)^0.5) 
             + arctan(T + RH) - arctan(RH - 1.676331)
             + 0.00391838 * RH^1.5 * arctan(0.023101 * RH) - 4.686035
     * Works for T in Celsius, RH in percentage
     * Add to dataframe as 'wet_bulb_temp_c' column
   
   - generate_data_quality_report(df_json: str) -> str (JSON)
     * Returns dict with: missing_pct per column, total_rows, 
       valid_rows, ikwtr_out_of_range_count (valid: 0.3-2.0),
       data_quality_score (0-100), quality_flag ("PASS"/"WARN"/"FAIL")
     * FAIL if any core column > 15% missing
     * WARN if 5-15% missing

3. backend/agents/agent_definitions.py (Agent 1 only for now)
   - Create Agent 1 using CrewAI Agent class
   - role: "HVAC Data Ingestion Specialist"
   - goal: "Transform raw building energy CSVs into a clean, validated, 
     feature-engineered dataset ready for HVAC performance analysis"
   - tools: [load_bdg2_datasets, engineer_hvac_features, 
             derive_wet_bulb_temperature, generate_data_quality_report]
   - verbose: True

Use Python type hints throughout. Add docstrings to every function.
```

### Test Method
```python
# tests/test_data_tools.py

import pytest
import pandas as pd
import json
from backend.agents.tools.data_tools import load_bdg2_datasets, engineer_hvac_features
from backend.agents.tools.thermo_tools import derive_wet_bulb_temperature, generate_data_quality_report

def test_wbt_derivation():
    """Stull equation: 30°C, 60% RH → ~23.5°C WBT"""
    wbt = derive_wet_bulb_temperature(30.0, 60.0)
    assert 22.0 < wbt < 25.0, f"WBT out of expected range: {wbt}"

def test_wbt_extreme_dry():
    """Dry air: WBT should be well below dry-bulb"""
    wbt = derive_wet_bulb_temperature(35.0, 10.0)
    assert wbt < 20.0

def test_wbt_saturated():
    """Saturated air (100% RH): WBT == Dry-bulb"""
    wbt = derive_wet_bulb_temperature(25.0, 100.0)
    assert abs(wbt - 25.0) < 1.0

def test_feature_engineering_columns(sample_df_json):
    """Check all expected columns exist after feature engineering"""
    result = engineer_hvac_features(sample_df_json)
    df = pd.DataFrame(json.loads(result)["data"])
    required = ["hour_of_day", "day_of_week", "is_weekend", 
                "rolling_avg_24h", "load_category", "iKW_TR"]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"

def test_data_quality_report_pass(sample_df_json):
    """Clean data should return PASS"""
    report = json.loads(generate_data_quality_report(sample_df_json))
    assert report["quality_flag"] in ["PASS", "WARN"]
    assert 0 <= report["data_quality_score"] <= 100

# Run:
# pytest tests/test_data_tools.py -v
```

---

## PHASE 2 — Performance Analyzer (Agent 2)
**Duration:** 3–4 hours | **Goal:** Anomaly detection + root cause classification

### What to Build
- Isolation Forest anomaly detector (multivariate)
- Z-score univariate validator
- Root cause classifier (rule-based + ML)
- Degradation trend scorer
- Agent 2 definition

### AI Prompt
```
Build the Performance Analyzer module for a HVAC multi-agent system.

Create backend/agents/tools/anomaly_tools.py with these @tool functions:

1. detect_anomalies_isolation_forest(data_json: str) -> str (JSON)
   - Features to use: ['meter_reading', 'iKW_TR', 'air_temperature', 'relative_humidity']
   - IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
   - StandardScaler before fitting
   - Add column 'anomaly_if' (1=anomaly, 0=normal) to dataframe
   - Return JSON with: anomaly_count, anomaly_pct, anomaly_timestamps (list)

2. validate_anomalies_zscore(data_json: str, column: str) -> str (JSON)
   - Compute Z-score for given column
   - Flag |Z| > 3.0 as anomaly in column 'anomaly_z_{column}'
   - Return JSON with flagged rows (timestamp, value, z_score)

3. classify_root_cause(anomaly_data_json: str) -> str (JSON)
   - For each anomaly row, apply these rules:
     WEATHER-DRIVEN: if air_temperature deviation > 2 std AND iKW_TR deviation < 1 std
     EQUIPMENT-DRIVEN: if iKW_TR > 0.85 kW/TR (poor efficiency) regardless of weather
     BEHAVIORAL: if anomaly occurs 09:00-18:00 on weekday AND temp is normal
     UNKNOWN: default if no rule matches
   - Return JSON list: [{timestamp, root_cause, confidence, description}]
   - description must be a 1-sentence human-readable explanation

4. score_degradation_trend(data_json: str) -> str (JSON)
   - Compute 7-day and 30-day rolling mean of iKW_TR
   - If 30-day mean > benchmark (0.60) by >10%: "degrading"
   - If 30-day mean < benchmark by >5%: "improving"  
   - Else: "stable"
   - Degradation score (0-100): 0=perfect, 100=critical
     Formula: min(100, max(0, (mean_ikwtr - 0.60) / 0.60 * 100))
   - Return JSON: {trend_status, degradation_score, 7d_mean_ikwtr, 30d_mean_ikwtr, benchmark}

5. generate_efficiency_scorecard(data_json: str) -> str (JSON)
   - Compute: avg_ikwtr, min_ikwtr, max_ikwtr, pct_time_above_benchmark
   - Efficiency grade: A (< 0.55), B (0.55-0.65), C (0.65-0.75), D (0.75-0.85), F (> 0.85)
   - Return JSON scorecard

Add Agent 2 to agent_definitions.py:
- role: "HVAC Performance Diagnostician"  
- goal: "Identify HVAC inefficiencies, detect anomalies, classify root causes, 
  and quantify system degradation using multi-parameter analysis"
- tools: [detect_anomalies_isolation_forest, validate_anomalies_zscore,
          classify_root_cause, score_degradation_trend, generate_efficiency_scorecard]
```

### Test Method
```python
# tests/test_anomaly_tools.py

import pytest
import json
import pandas as pd
import numpy as np
from backend.agents.tools.anomaly_tools import (
    detect_anomalies_isolation_forest,
    validate_anomalies_zscore,
    classify_root_cause,
    score_degradation_trend
)

def test_isolation_forest_detects_injected_anomalies():
    """Inject obvious anomalies and verify detection"""
    # Create normal data
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        'timestamp': pd.date_range('2018-01-01', periods=n, freq='H'),
        'meter_reading': np.random.normal(100, 10, n),
        'iKW_TR': np.random.normal(0.60, 0.05, n),
        'air_temperature': np.random.normal(25, 3, n),
        'relative_humidity': np.random.normal(60, 5, n),
    })
    # Inject 10 obvious anomalies
    df.loc[50:59, 'iKW_TR'] = 2.5  # way above 0.60 benchmark
    
    result = json.loads(detect_anomalies_isolation_forest(df.to_json()))
    assert result['anomaly_count'] > 0
    assert result['anomaly_pct'] < 10  # contamination=0.05

def test_zscore_flags_outliers():
    """Z-score should flag values beyond 3 std"""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2018-01-01', periods=100, freq='H'),
        'iKW_TR': [0.60] * 99 + [5.0]  # last value is extreme outlier
    })
    result = json.loads(validate_anomalies_zscore(df.to_json(), 'iKW_TR'))
    assert len(result['flagged_rows']) >= 1
    assert result['flagged_rows'][0]['z_score'] > 3.0

def test_root_cause_equipment_driven():
    """High iKW-TR regardless of weather = equipment fault"""
    anomaly = {
        'air_temperature': 25.0,  # normal temp
        'air_temperature_zscore': 0.2,  # no deviation
        'iKW_TR': 0.92,  # very high = poor chiller
        'iKW_TR_zscore': 3.5,
        'hour_of_day': 3,
        'is_weekend': False
    }
    result = json.loads(classify_root_cause(json.dumps([anomaly])))
    assert result[0]['root_cause'] == 'EQUIPMENT-DRIVEN'

def test_degradation_score_range():
    """Degradation score must always be 0-100"""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2018-01-01', periods=720, freq='H'),
        'iKW_TR': np.random.normal(0.70, 0.05, 720)
    })
    result = json.loads(score_degradation_trend(df.to_json()))
    assert 0 <= result['degradation_score'] <= 100

# pytest tests/test_anomaly_tools.py -v
```

---

## PHASE 3 — Forecasting Agent (Agent 3)
**Duration:** 3–4 hours | **Goal:** 24h & 168h energy forecasts with confidence intervals

### What to Build
- Prophet forecasting wrapper
- XGBoost fallback forecaster
- Open-Meteo weather API integration
- Peak demand detection
- Agent 3 definition

### AI Prompt
```
Build the Forecasting module for a HVAC multi-agent system.

Create backend/agents/tools/forecast_tools.py and weather_tools.py:

1. backend/agents/tools/weather_tools.py
   @tool fetch_weather_forecast(lat: float, lon: float, days: int) -> str (JSON)
   - Call Open-Meteo API: https://api.open-meteo.com/v1/forecast
   - Parameters: latitude, longitude, hourly=temperature_2m,relativehumidity_2m,
     dewpoint_2m, forecast_days=days
   - Handle timeout (10s), retry 3 times with 2s backoff
   - Return JSON: {hourly: [{timestamp, temperature_2m, relativehumidity_2m}]}
   - On failure: return last known weather from data (graceful degradation)

2. backend/agents/tools/forecast_tools.py

   @tool run_prophet_forecast(data_json: str, horizon_hours: int) -> str (JSON)
   - Prepare Prophet dataframe: rename timestamp→ds, meter_reading→y
   - Add regressors: air_temperature, relative_humidity, is_weekend
   - Fit model with: yearly_seasonality=True, weekly_seasonality=True, 
     daily_seasonality=True, seasonality_mode='multiplicative'
   - Generate forecast for horizon_hours
   - Return JSON: {
       model_used: "prophet",
       horizon_hours: int,
       forecast: [{ds, yhat, yhat_lower, yhat_upper}],  # 95% CI
       mape_on_training: float,
       peak_hours: [int]  # hours where yhat > 90th percentile
     }
   - Minimum 168 rows required; raise ValueError if insufficient

   @tool run_xgboost_forecast(data_json: str, horizon_hours: int) -> str (JSON)
   - Features: hour_of_day, day_of_week, month, is_weekend, 
     air_temperature, relative_humidity, rolling_avg_24h, lag_1h, lag_24h
   - XGBRegressor(n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42)
   - Train on all data, predict future using last-known weather features
   - Return same JSON structure as Prophet output but model_used: "xgboost"
   - No confidence intervals available: set yhat_lower=yhat*0.9, yhat_upper=yhat*1.1

   @tool predict_peak_demand_windows(forecast_json: str) -> str (JSON)
   - Parse forecast JSON
   - Find continuous windows where yhat > 85th percentile
   - Return: [{start_time, end_time, peak_yhat_kwh, duration_hours, 
               pre_cool_recommendation: "Pre-cool by {N} hours"}]
   - Pre-cool window = 1-2 hours before each peak window starts

   @tool select_best_forecast_model(data_json: str, horizon_hours: int) -> str (JSON)
   - Try Prophet first; if rows < 168 or error, fallback to XGBoost
   - Log which model was used and why
   - Return forecast result from whichever model succeeded

Add Agent 3 to agent_definitions.py:
- role: "Energy Demand Forecaster"
- goal: "Predict HVAC energy consumption for 24-168 hours ahead with 
  weather-adjusted confidence intervals to enable proactive operations"
- tools: [fetch_weather_forecast, select_best_forecast_model, 
          run_prophet_forecast, run_xgboost_forecast, predict_peak_demand_windows]
```

### Test Method
```python
# tests/test_forecast_tools.py

import pytest
import json
import pandas as pd
import numpy as np
from backend.agents.tools.forecast_tools import (
    run_prophet_forecast, run_xgboost_forecast, predict_peak_demand_windows
)
from backend.agents.tools.weather_tools import fetch_weather_forecast

def make_sample_df(n_hours=720):
    """720 hours = 30 days"""
    np.random.seed(42)
    timestamps = pd.date_range('2018-01-01', periods=n_hours, freq='H')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'meter_reading': 100 + 30 * np.sin(np.arange(n_hours) * 2 * np.pi / 24) 
                         + np.random.normal(0, 5, n_hours),
        'air_temperature': 25 + 5 * np.sin(np.arange(n_hours) * 2 * np.pi / 24),
        'relative_humidity': np.random.normal(60, 10, n_hours).clip(20, 100),
        'is_weekend': [1 if pd.Timestamp(t).weekday() >= 5 else 0 for t in timestamps],
        'rolling_avg_24h': np.random.normal(100, 5, n_hours),
        'hour_of_day': [t.hour for t in timestamps],
        'day_of_week': [t.weekday() for t in timestamps],
        'month': [t.month for t in timestamps],
    })
    return df

def test_prophet_returns_correct_horizon():
    df = make_sample_df(720)
    result = json.loads(run_prophet_forecast(df.to_json(), 24))
    assert result['model_used'] == 'prophet'
    assert len(result['forecast']) == 24

def test_prophet_confidence_intervals():
    """yhat_lower <= yhat <= yhat_upper for all rows"""
    df = make_sample_df(720)
    result = json.loads(run_prophet_forecast(df.to_json(), 24))
    for row in result['forecast']:
        assert row['yhat_lower'] <= row['yhat'] <= row['yhat_upper'], \
            f"CI violated: {row}"

def test_xgboost_fallback_works():
    """XGBoost should work even with 48 rows (too few for Prophet)"""
    df = make_sample_df(48)
    result = json.loads(run_xgboost_forecast(df.to_json(), 24))
    assert result['model_used'] == 'xgboost'
    assert len(result['forecast']) == 24

def test_peak_detection_finds_peaks():
    df = make_sample_df(720)
    forecast = json.loads(run_prophet_forecast(df.to_json(), 168))
    peaks = json.loads(predict_peak_demand_windows(json.dumps(forecast)))
    assert isinstance(peaks, list)
    for peak in peaks:
        assert 'start_time' in peak
        assert 'pre_cool_recommendation' in peak

def test_weather_api_returns_structure():
    """Test Open-Meteo API (requires internet)"""
    result = json.loads(fetch_weather_forecast(13.08, 80.27, 3))
    assert 'hourly' in result
    assert len(result['hourly']) > 0
    assert 'temperature_2m' in result['hourly'][0]

# pytest tests/test_forecast_tools.py -v -k "not weather_api"  # skip API test if offline
```

---

## PHASE 4 — Optimization & Recommendation Agent (Agent 4)
**Duration:** 2–3 hours | **Goal:** Ranked, explainable recommendations

### What to Build
- Setpoint optimizer
- Chiller sequencing logic
- Load-shift planner
- Maintenance priority scorer
- ChromaDB memory integration
- Agent 4 definition

### AI Prompt
```
Build the Optimization & Recommendation module for a HVAC multi-agent system.

Create backend/agents/tools/optimization_tools.py:

1. @tool optimize_setpoints(efficiency_scorecard_json: str, ambient_temp_c: float) -> str (JSON)
   Rules-based optimization:
   - If avg_ikwtr > 0.75 AND ambient_temp < 30: 
     Recommend raising chilled water setpoint by 1-2°C 
     (warmer setpoint = less compressor work = lower kW/TR)
   - If avg_ikwtr > 0.80: 
     Recommend immediate chiller inspection (efficiency F grade)
   - If ambient_temp > 35: 
     Recommend lowering condenser water approach temperature
   - Return: [{action, expected_ikwtr_improvement, expected_kwh_saving_pct, 
               rationale, priority (1-5, 1=highest)}]

2. @tool recommend_chiller_sequencing(load_pct: float, num_chillers: int) -> str (JSON)
   Sequencing logic:
   - < 40% load: Run 1 chiller at full load (more efficient than 2 at 20%)
   - 40-70% load: Run 2 chillers at 50-60% each
   - 70-90% load: Run 2 chillers, prep 3rd
   - > 90% load: All chillers
   - Return: {recommended_active_chillers, each_chiller_load_pct, 
              efficiency_gain_pct, rationale}

3. @tool plan_load_shifting(peak_windows_json: str) -> str (JSON)
   - For each peak window: calculate how many hours before to start pre-cooling
   - Pre-cooling: lower setpoint by 1°C for 1-2 hours before peak
   - Estimated saving: 5-15% demand charge reduction
   - Return: [{peak_start, pre_cool_start, pre_cool_action, 
               estimated_demand_saving_pct, rationale}]

4. @tool score_maintenance_priority(anomaly_report_json: str, 
                                     degradation_score: float) -> str (JSON)
   - Priority score formula:
     score = (anomaly_count * 10) + (degradation_score * 0.5) + 
             (pct_time_above_benchmark * 0.3)
   - Cap at 100
   - Priority levels: CRITICAL (>80), HIGH (60-80), MEDIUM (40-60), LOW (<40)
   - Return: {priority_level, priority_score, recommended_maintenance_action,
              urgency_days (how soon to act), rationale}

5. @tool compile_final_recommendations(setpoints_json: str, sequencing_json: str,
                                        load_shift_json: str, maintenance_json: str) -> str (JSON)
   - Merge all recommendations into one ranked list
   - Sort by priority (1 = highest)
   - Limit to top 10 recommendations
   - Each recommendation must have: rank, category, action, rationale, 
     expected_impact, priority_score
   - Return: {total_recommendations: int, recommendations: [list]}

Create backend/agents/tools/memory_tools.py:
@tool store_recommendations_in_memory(recommendations_json: str, run_id: str) -> str
   - Use ChromaDB embedded client
   - Collection: "hvac_recommendations"  
   - For each recommendation: embed the 'action' + 'rationale' as document
   - Metadata: {run_id, category, priority_score, timestamp}

@tool query_similar_past_recommendations(query: str) -> str (JSON)
   - Query ChromaDB collection with query text
   - Return top 3 similar past recommendations with their run_ids
   - Used to avoid repeating same recommendation every run

Add Agent 4 to agent_definitions.py.
```

### Test Method
```python
# tests/test_optimization_tools.py

import pytest
import json
from backend.agents.tools.optimization_tools import (
    optimize_setpoints, recommend_chiller_sequencing,
    plan_load_shifting, score_maintenance_priority,
    compile_final_recommendations
)

def test_setpoint_optimization_high_ikwtr():
    scorecard = json.dumps({"avg_ikwtr": 0.82, "efficiency_grade": "F"})
    result = json.loads(optimize_setpoints(scorecard, 28.0))
    assert len(result) > 0
    actions = [r['action'] for r in result]
    assert any('setpoint' in a.lower() or 'inspect' in a.lower() for a in actions)

def test_chiller_sequencing_low_load():
    """< 40% load should recommend 1 chiller"""
    result = json.loads(recommend_chiller_sequencing(30.0, 3))
    assert result['recommended_active_chillers'] == 1

def test_chiller_sequencing_high_load():
    """90%+ load should activate all chillers"""
    result = json.loads(recommend_chiller_sequencing(95.0, 3))
    assert result['recommended_active_chillers'] == 3

def test_maintenance_score_in_range():
    anomaly_report = json.dumps({"anomaly_count": 15, "pct_time_above_benchmark": 40})
    result = json.loads(score_maintenance_priority(anomaly_report, 65.0))
    assert 0 <= result['priority_score'] <= 100
    assert result['priority_level'] in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

def test_rationale_not_empty():
    """Every recommendation must have a non-empty rationale"""
    scorecard = json.dumps({"avg_ikwtr": 0.75, "efficiency_grade": "D"})
    result = json.loads(optimize_setpoints(scorecard, 32.0))
    for rec in result:
        assert len(rec.get('rationale', '')) > 20, "Rationale too short"

def test_compile_max_10_recommendations():
    """Final list must cap at 10"""
    # Build dummy inputs
    dummy = json.dumps([{"action": f"Action {i}", "rationale": "test", 
                         "priority": i, "category": "test", 
                         "expected_impact": "low", "priority_score": i*10} 
                        for i in range(1, 15)])
    result = json.loads(compile_final_recommendations(dummy, dummy, dummy, dummy))
    assert result['total_recommendations'] <= 10

# pytest tests/test_optimization_tools.py -v
```

---

## PHASE 5 — Report Generation Agent (Agent 5)
**Duration:** 3–4 hours | **Goal:** PDF + HTML technical decision report

### What to Build
- Jinja2 HTML report template
- Plotly chart generation (4 charts minimum)
- WeasyPrint PDF conversion
- Agent 5 definition
- Full report output structure

### AI Prompt
```
Build the Decision Report module for a HVAC multi-agent system.

1. Create backend/templates/report_template.html
   A professional HTML report template with:
   - Header: "HVAC Optimization Decision Report", building_id, run date
   - Section 1: Executive Summary (2-3 auto-generated sentences from agent outputs)
   - Section 2: Data Quality Scorecard (table: column, completeness%, quality_flag)
   - Section 3: Efficiency Dashboard
     * Current avg iKW-TR vs. benchmark (0.60) — big number display
     * Efficiency grade badge (A/B/C/D/F with color coding)
     * 30-day trend (up/down arrow + percentage)
   - Section 4: Anomaly Log (table: timestamp, parameter, severity, root_cause, description)
   - Section 5: Energy Forecast (placeholder for chart images — base64 PNG)
   - Section 6: Top 5 Recommendations
     * Each card: rank badge, category tag, action text, rationale, expected impact
     * Color coded by priority (red=critical, orange=high, yellow=medium, green=low)
   - Section 7: Maintenance Priority
     * Priority level badge (CRITICAL/HIGH/MEDIUM/LOW)
     * Urgency: "Act within N days"
     * Recommended action
   - Professional CSS styling inline (no external CSS files)
   - Print-friendly (works with WeasyPrint)

2. Create backend/agents/tools/report_tools.py

   @tool generate_forecast_chart(forecast_json: str) -> str
   - Plotly line chart: x=timestamp, y=yhat with yhat_lower/upper shaded area
   - Add vertical line at "now" to separate history from forecast
   - Title: "24-Hour Energy Demand Forecast with 95% Confidence Interval"
   - Export as base64 PNG string (for embedding in HTML)
   - Use plotly.io.to_image(format='png')

   @tool generate_efficiency_trend_chart(data_json: str) -> str
   - Plotly line chart: x=timestamp, y=iKW_TR
   - Add horizontal dashed line at benchmark=0.60
   - Add horizontal dashed line at poor=0.85
   - Color the line: green < 0.65, yellow 0.65-0.80, red > 0.80
   - Title: "iKW-TR Efficiency Trend (Benchmark: 0.60 kW/TR)"
   - Return base64 PNG

   @tool generate_energy_heatmap(data_json: str) -> str
   - Plotly heatmap: x=hour_of_day (0-23), y=day_of_week, z=avg meter_reading
   - Shows energy consumption patterns by hour and day
   - Title: "Energy Consumption Heatmap (kWh by Hour and Day)"
   - Return base64 PNG

   @tool render_html_report(
       data_quality_json, efficiency_scorecard_json,
       anomaly_report_json, forecast_json,
       recommendations_json, maintenance_json,
       building_id: str, run_id: str
   ) -> str
   - Load Jinja2 template from backend/templates/report_template.html
   - Generate all 3 charts (base64)
   - Render template with all data
   - Write to reports/html/{run_id}.html
   - Return file path

   @tool generate_pdf_report(html_path: str) -> str
   - Use WeasyPrint: HTML(filename=html_path).write_pdf(pdf_path)
   - Write to reports/pdf/{run_id}.pdf
   - Return pdf_path
   - On failure: log error, return None (PDF optional, HTML mandatory)

Add Agent 5 to agent_definitions.py.
```

### Test Method
```python
# tests/test_report_tools.py

import pytest
import os
import json
import base64
from backend.agents.tools.report_tools import (
    generate_forecast_chart, generate_efficiency_trend_chart,
    render_html_report
)

def test_forecast_chart_is_valid_base64():
    """Chart should return valid base64 PNG"""
    forecast = json.dumps({
        "forecast": [
            {"ds": "2018-02-01 00:00:00", "yhat": 100, "yhat_lower": 90, "yhat_upper": 110}
            for _ in range(24)
        ]
    })
    result = generate_forecast_chart(forecast)
    # Should not raise exception
    decoded = base64.b64decode(result)
    assert decoded[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic bytes

def test_html_report_file_created(tmp_path, monkeypatch):
    """HTML file must be created at expected path"""
    monkeypatch.chdir(tmp_path)
    os.makedirs("reports/html", exist_ok=True)
    os.makedirs("reports/pdf", exist_ok=True)
    
    result = render_html_report(
        data_quality_json='{"quality_flag": "PASS", "data_quality_score": 92}',
        efficiency_scorecard_json='{"avg_ikwtr": 0.68, "efficiency_grade": "C"}',
        anomaly_report_json='{"anomaly_count": 3, "anomalies": []}',
        forecast_json='{"forecast": []}',
        recommendations_json='{"recommendations": []}',
        maintenance_json='{"priority_level": "MEDIUM", "priority_score": 45}',
        building_id="building_001",
        run_id="test_run_001"
    )
    assert os.path.exists(result)
    
    with open(result) as f:
        content = f.read()
    assert "HVAC Optimization Decision Report" in content
    assert "building_001" in content

# pytest tests/test_report_tools.py -v
```

---

## PHASE 6 — CrewAI Pipeline Assembly
**Duration:** 2–3 hours | **Goal:** All 5 agents running end-to-end

### What to Build
- Task definitions for all 5 agents
- Crew assembly with sequential process
- Pipeline orchestration function
- Full end-to-end integration test

### AI Prompt
```
Assemble the complete CrewAI pipeline for the HVAC multi-agent system.

1. Create backend/agents/task_definitions.py
   Define 5 Task objects (one per agent) with:
   
   Task 1 — ingest_task:
   - description: "Load the HVAC datasets from {dataset_path}, {weather_path}, 
     {metadata_path}. Validate data quality. Engineer all features including 
     iKW-TR derivation and WBT calculation. Return a JSON summary of the 
     clean dataset."
   - expected_output: "JSON string containing: data_quality_report, 
     processed_data_path, feature_summary, row_count, column_list"
   - agent: ingestion_agent

   Task 2 — analyze_task:
   - description: "Using the clean dataset from Task 1, run Isolation Forest 
     and Z-score anomaly detection. Classify root causes for all detected 
     anomalies. Score the 30-day degradation trend. Generate the efficiency 
     scorecard with iKW-TR grade."
   - expected_output: "JSON containing: anomaly_report, efficiency_scorecard, 
     degradation_score, root_cause_summary"
   - agent: analyzer_agent
   - context: [ingest_task]

   Task 3 — forecast_task:
   - description: "Generate {forecast_horizon_hours}-hour energy demand forecast 
     for building at latitude {lat}, longitude {lon}. Fetch current weather 
     forecast. Identify peak demand windows and pre-cooling opportunities."
   - expected_output: "JSON containing: forecast_24h, forecast_168h, 
     peak_windows, model_used, mape"
   - agent: forecasting_agent
   - context: [ingest_task]

   Task 4 — optimize_task:
   - description: "Based on the anomaly analysis and energy forecast, generate 
     the top optimization recommendations. Include setpoint adjustments, 
     chiller sequencing, load shifting, and maintenance priority scoring. 
     Query memory for past recommendations to avoid repetition."
   - expected_output: "JSON containing: ranked recommendations list (max 10), 
     maintenance_priority, total_expected_savings_pct"
   - agent: optimizer_agent
   - context: [analyze_task, forecast_task]

   Task 5 — report_task:
   - description: "Consolidate all agent outputs into a complete technical 
     decision report. Generate all visualization charts. Render HTML report 
     and convert to PDF. Save both files."
   - expected_output: "JSON containing: html_report_path, pdf_report_path, 
     report_summary (executive summary text)"
   - agent: reporter_agent
   - context: [ingest_task, analyze_task, forecast_task, optimize_task]

2. Create backend/agents/crew.py
   def build_hvac_crew() -> Crew:
       return Crew(
           agents=[ingestion_agent, analyzer_agent, forecasting_agent, 
                   optimizer_agent, reporter_agent],
           tasks=[ingest_task, analyze_task, forecast_task, optimize_task, report_task],
           process=Process.sequential,
           verbose=True,
           memory=True  # enables ChromaDB memory
       )

3. Create backend/pipeline.py
   async def run_pipeline(run_id: str, inputs: dict) -> dict:
       - Update DB: status = "running"
       - Build crew, kickoff with inputs
       - Parse final result
       - Update DB: status = "completed", duration_s
       - Return result dict

4. Update backend/routers/pipeline.py
   POST /api/v1/pipeline/run → triggers run_pipeline as background task
   GET /api/v1/pipeline/status/{run_id} → reads from DB
```

### Test Method
```python
# tests/test_pipeline_api.py

import pytest
import httpx
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_pipeline_run_and_complete():
    """Integration test: full pipeline runs end-to-end"""
    # Start pipeline
    response = httpx.post(f"{BASE_URL}/pipeline/run", json={
        "dataset_path": "tests/fixtures/sample_data.csv",
        "weather_path": "tests/fixtures/sample_weather.csv",
        "metadata_path": "tests/fixtures/sample_metadata.csv",
        "building_id": "test_building",
        "forecast_horizon_hours": 24,
        "lat": 13.08,
        "lon": 80.27
    })
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    # Poll until complete (max 10 minutes)
    for _ in range(60):
        status_response = httpx.get(f"{BASE_URL}/pipeline/status/{run_id}")
        status = status_response.json()["status"]
        if status == "completed":
            break
        elif status == "failed":
            pytest.fail(f"Pipeline failed: {status_response.json()}")
        time.sleep(10)
    else:
        pytest.fail("Pipeline timed out after 10 minutes")

    # Check report was generated
    report_response = httpx.get(f"{BASE_URL}/reports/{run_id}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert "html_path" in report
    assert "summary" in report
    assert report["summary"]["total_anomalies"] >= 0

# Run server first: uvicorn backend.main:app --port 8000
# pytest tests/test_pipeline_api.py -v -s
```

---

## PHASE 7 — FastAPI Complete + SQLite Persistence
**Duration:** 1–2 hours | **Goal:** All API endpoints working with DB persistence

### AI Prompt
```
Complete the FastAPI backend for the HVAC multi-agent system.

1. Update backend/database.py with full schema:
   Tables (SQLAlchemy models):
   - PipelineRun: run_id, building_id, status, created_at, completed_at, duration_s, error_msg
   - AgentOutput: id, run_id, agent_name, output_json, created_at
   - Recommendation: id, run_id, rank, category, action, rationale, 
                     expected_impact, priority_score, created_at
   - AnomalyLog: id, run_id, timestamp, parameter, severity, root_cause, description
   - ForecastResult: id, run_id, horizon_hours, model_used, mape, created_at

2. Create backend/routers/reports.py:
   GET /api/v1/reports/{run_id} 
   → returns HTML content + PDF path + summary
   
   GET /api/v1/reports/{run_id}/pdf
   → streams PDF file as FileResponse
   
   GET /api/v1/history
   → lists last 20 pipeline runs with status and summary

3. Create backend/routers/data.py:
   POST /api/v1/data/upload
   → accepts multipart file upload, saves to data/raw/
   → validates file is CSV with required columns
   → returns {filename, rows, columns, validation_status}

4. Add CORS middleware to main.py:
   Allow origins: ["http://localhost:3000", "app://.", "file://"]
   (Electron uses file:// and app:// origins)
```

### Test Method
```bash
# Manual API tests using curl

# Upload a CSV
curl -X POST http://localhost:8000/api/v1/data/upload \
  -F "file=@tests/fixtures/sample_data.csv"

# Get run history
curl http://localhost:8000/api/v1/history

# Get specific report
curl http://localhost:8000/api/v1/reports/run_001

# Download PDF
curl http://localhost:8000/api/v1/reports/run_001/pdf -o test_report.pdf
open test_report.pdf  # Should open a valid PDF
```

---

## PHASE 8 — Electron Frontend
**Duration:** 3–4 hours | **Goal:** Working desktop UI

### AI Prompt
```
Build an Electron desktop application for the HVAC multi-agent system.

Tech stack: Electron 29 + React 18 + TailwindCSS + Axios

Create frontend/ with:

1. main.js (Electron main process)
   - BrowserWindow: 1200x800, title "HVAC Intelligence System"
   - Load React app from localhost:3000 in dev, from build/ in prod
   - Enable contextIsolation, use preload.js
   - Menu: File > Upload Dataset, View > Toggle DevTools

2. src/App.jsx — Main app with 3 tabs:
   Tab 1: "Dashboard" — pipeline control + status
   Tab 2: "Report" — HTML report viewer
   Tab 3: "History" — past runs table

3. src/components/Dashboard.jsx
   - File upload section (3 file inputs: energy CSV, weather CSV, metadata CSV)
   - Building ID input + lat/lon inputs
   - "Run Analysis" button → POST to /api/v1/pipeline/run
   - Progress tracker showing 5 agent steps (each lights up when complete)
   - Status badge: QUEUED (grey) / RUNNING (blue spinner) / COMPLETED (green) / FAILED (red)
   - Auto-polls /api/v1/pipeline/status every 5 seconds while running
   - On completion: auto-switches to Report tab

4. src/components/ReportViewer.jsx
   - Renders HTML report content in a sandboxed iframe
   - "Download PDF" button → GET /api/v1/reports/{run_id}/pdf
   - "Open in Browser" button
   - Show report metadata: generated_at, building_id, anomaly_count, efficiency_grade

5. src/components/History.jsx
   - Table: Run ID | Building | Date | Status | Anomalies | Grade | Actions
   - "View Report" button per row

Design requirements:
- Dark professional theme (bg: #0f172a, cards: #1e293b, accent: #3b82f6)
- Use Lucide icons for all icons
- Responsive for 1200px minimum width
- Loading skeletons while API calls are pending
```

### Test Method
```bash
# Start backend
cd backend && uvicorn main:app --reload --port 8000 &

# Start Electron in dev mode
cd frontend
npm install
npm run dev   # Starts React dev server + Electron window

# Manual tests:
# 1. Upload sample CSV files → verify file names appear in UI
# 2. Click "Run Analysis" → verify spinner appears
# 3. Watch 5 agent steps light up sequentially
# 4. On completion → Report tab should auto-open with rendered HTML
# 5. Click "Download PDF" → PDF should download
# 6. Check History tab → run should appear in table
```

---

## PHASE 9 — Testing, Code Quality & GitHub Push
**Duration:** 2–3 hours | **Goal:** Clean repo ready for portfolio

### AI Prompt
```
Add final testing, code quality setup, and documentation for the HVAC 
multi-agent system GitHub repository.

1. Create tests/fixtures/generate_fixtures.py
   Script that generates minimal test fixtures:
   - sample_data.csv: 720 rows (30 days hourly), columns: 
     timestamp, meter_reading, air_temperature, relative_humidity, dew_temperature
   - sample_weather.csv: matching weather data
   - sample_metadata.csv: 1 building row
   Generate with realistic patterns (sinusoidal daily load curve, noise)

2. Create pytest.ini:
   [pytest]
   testpaths = tests
   addopts = --cov=backend --cov-report=term-missing --cov-fail-under=70

3. Create .pre-commit-config.yaml:
   repos:
   - repo: black (24.2.0)
   - repo: ruff (0.3.2)
   - repo: mypy (1.8.0) on backend/ only

4. Create a complete README.md with:
   - Project title + 1-paragraph description
   - Architecture diagram (ASCII)
   - Tech stack badges
   - Quickstart (clone → install → run → open)
   - Dataset instructions (BDG2 download steps)
   - Screenshots section (placeholder)
   - API reference table (endpoints)
   - Agent descriptions table
   - License: MIT

5. Create .env.example:
   GEMINI_API_KEY=your_gemini_key_here   # Required for CrewAI LLM — get free at aistudio.google.com
   DATABASE_URL=sqlite:///./hvac_system.db
   REPORTS_DIR=reports
   DATA_DIR=data
   LOG_LEVEL=INFO

6. Ensure .gitignore includes:
   .env, data/raw/, data/processed/, reports/, models/saved/,
   __pycache__/, *.pyc, .pytest_cache/, htmlcov/,
   node_modules/, frontend/build/, *.db
```

### Final Test & Push
```bash
# Run full test suite
pytest tests/ -v --cov=backend --cov-report=term-missing

# Check coverage
# Target: ≥ 70% coverage

# Format and lint
black backend/
ruff check backend/ --fix

# Generate requirements.txt
pip freeze > requirements.txt

# Initialize git and push
git init
git add .
git commit -m "feat: initial production-grade HVAC multi-agent system

- 5-agent CrewAI pipeline: Ingestion → Analysis → Forecast → Optimize → Report
- Core parameters: kWh, iKW-TR (derived), Ambient conditions, Load profiles
- Anomaly detection: Isolation Forest + Z-score with root cause classification
- Forecasting: Prophet (primary) + XGBoost (fallback), 24h and 168h horizons
- Optimization: setpoint, chiller sequencing, load shifting recommendations
- Reports: automated PDF/HTML with Plotly charts
- Backend: FastAPI + SQLite | Frontend: Electron + React
- Dataset: Building Data Genome Project 2 (BDG2)
- Test coverage: ≥ 70%"

git remote add origin https://github.com/yourusername/hvac-multiagent-system.git
git push -u origin main
```

---

## Summary: Full Phase Timeline

| Phase | What | Time | Commit Message |
|-------|------|------|----------------|
| 0 | Project Setup | 30 min | `chore: project structure and boilerplate` |
| 1 | Agent 1 — Ingestion | 2-3h | `feat: data ingestion agent with iKW-TR and WBT derivation` |
| 2 | Agent 2 — Analyzer | 3-4h | `feat: performance analyzer with anomaly detection and root cause` |
| 3 | Agent 3 — Forecaster | 3-4h | `feat: forecasting agent with Prophet and XGBoost` |
| 4 | Agent 4 — Optimizer | 2-3h | `feat: optimization agent with setpoint and sequencing recommendations` |
| 5 | Agent 5 — Reporter | 3-4h | `feat: report agent with PDF/HTML generation and Plotly charts` |
| 6 | Pipeline Assembly | 2-3h | `feat: CrewAI crew assembled, end-to-end pipeline working` |
| 7 | FastAPI Complete | 1-2h | `feat: complete REST API with DB persistence` |
| 8 | Electron Frontend | 3-4h | `feat: Electron desktop UI with dashboard and report viewer` |
| 9 | Tests + GitHub | 2-3h | `chore: test suite, code quality, README, initial push` |

**Total estimated time: 22–32 hours of focused development**
