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

from backend.agents.tools.optimization_tools import (
    optimize_setpoints,
    recommend_chiller_sequencing,
    plan_load_shifting,
    score_maintenance_priority,
    compile_final_recommendations
)

from backend.agents.tools.memory_tools import (
    store_recommendations_in_memory,
    query_similar_past_recommendations
)

from backend.agents.tools.report_tools import (
    generate_forecast_chart,
    generate_efficiency_trend_chart,
    generate_energy_heatmap,
    render_html_report,
    generate_pdf_report
)

ingestion_agent = Agent(
    role="Data Engineer",
    goal="Transform raw CSVs into a clean, analysis-ready dataframe",
    backstory="Expert in building energy data pipelines and sensor data quality.",
    tools=[],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

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

optimizer_agent = Agent(
    role="HVAC Optimization Engineer",
    goal="Convert analytical insights into safe, explainable operational actions",
    backstory="Energy consultant who has optimized HVAC systems across 50+ commercial buildings.",
    tools=[
        optimize_setpoints,
        recommend_chiller_sequencing,
        plan_load_shifting,
        score_maintenance_priority,
        compile_final_recommendations,
        store_recommendations_in_memory,
        query_similar_past_recommendations
    ],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

reporter_agent = Agent(
    role="Technical Report Writer",
    goal="Produce a clear, complete, and actionable technical decision report",
    backstory="Engineering documentation specialist who translates AI outputs into operational clarity.",
    tools=[
        generate_forecast_chart,
        generate_efficiency_trend_chart,
        generate_energy_heatmap,
        render_html_report,
        generate_pdf_report
    ],
    llm=llm,
    verbose=True,
    allow_delegation=False
)
