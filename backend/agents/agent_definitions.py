from crewai import Agent
from backend.llm import llm 
from backend.agents.tools.anomaly_tools import (
    detect_anomalies_isolation_forest,
    validate_anomalies_zscore,
    classify_root_cause,
    score_degradation_trend,
    generate_efficiency_scorecard
)

from backend.agents.tools.weather_tools import fetch_weather_forecast
from backend.agents.tools.forecast_tools import (
    select_best_forecast_model,
    run_prophet_forecast,
    run_xgboost_forecast,
    predict_peak_demand_windows
)

# Placeholder for Agent 1 if needed later (Ingestion Agent)
# data_engineer = Agent(...)

analyzer_agent = Agent(
    role="HVAC Performance Diagnostician",
    goal="Identify HVAC inefficiencies, detect anomalies, classify root causes, and quantify system degradation using multi-parameter analysis",
    backstory="Senior MEP engineer with expertise in chiller plant diagnostics, analyzing multiple sensor points to find actionable inefficiencies.",
    tools=[
        detect_anomalies_isolation_forest,
        validate_anomalies_zscore,
        classify_root_cause,
        score_degradation_trend,
        generate_efficiency_scorecard
    ],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

forecast_agent = Agent(
    role="Energy Demand Forecaster",
    goal="Predict HVAC energy consumption for 24-168 hours ahead with weather-adjusted confidence intervals to enable proactive operations",
    backstory="Data scientist specializing in time-series energy forecasting",
    tools=[
        fetch_weather_forecast, 
        select_best_forecast_model, 
        run_prophet_forecast, 
        run_xgboost_forecast, 
        predict_peak_demand_windows
    ],
    llm=llm,
    verbose=True,
    allow_delegation=False
)
