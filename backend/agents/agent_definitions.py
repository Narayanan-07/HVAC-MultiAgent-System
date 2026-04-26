# backend/agents/agent_definitions.py

from crewai import Agent
from backend.llm import get_groq_llm, rate_limiter
from backend.agents.tools.anomaly_tools import (
    detect_anomalies_isolation_forest,
    validate_anomalies_zscore,
    classify_root_cause,
    score_degradation_trend,
    generate_efficiency_scorecard,
    generate_data_quality_report
)
from backend.agents.tools.data_tools import (
    load_and_prepare_hvac_data_tool,
    engineer_hvac_features_tool
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

# ============================================================================
# AGENT FACTORY with Fresh LLM instances (avoids state issues)
# ============================================================================

def create_ingestion_agent():
    """Data Engineer - No LLM calls needed (pre-processed)"""
    return Agent(
        role="Data Engineer",
        goal="Confirm pre-processed data is ready for analysis",
        backstory=(
            "Expert in building energy data pipelines. The data has already been pre-processed "
            "by an external pipeline. Your only job is to return the final summary."
        ),
        tools=[],
        llm=get_groq_llm(),
        verbose=True,
        allow_delegation=False,
        max_rpm=None,  # Remove limit, we control globally
        max_iter=5,  # Limit iterations to prevent loops
    )

def create_analyzer_agent():
    """Performance Diagnostician"""
    return Agent(
        role="HVAC Performance Diagnostician",
        goal="Identify HVAC inefficiencies, detect anomalies, classify root causes",
        backstory="Senior MEP engineer with expertise in chiller plant diagnostics",
        tools=[
            detect_anomalies_isolation_forest,
            validate_anomalies_zscore,
            classify_root_cause,
            score_degradation_trend,
            generate_efficiency_scorecard,
            generate_data_quality_report,
        ],
        llm=get_groq_llm(),
        verbose=True,
        allow_delegation=False,
        max_rpm=None,
        max_iter=5,
    )

def create_forecast_agent():
    """Energy Demand Forecaster"""
    return Agent(
        role="Energy Demand Forecaster",
        goal="Predict HVAC energy consumption 24-168 hours ahead",
        backstory="Data scientist specializing in time-series energy forecasting",
        tools=[
            fetch_weather_forecast, 
            select_best_forecast_model, 
            run_prophet_forecast, 
            run_xgboost_forecast, 
            predict_peak_demand_windows
        ],
        llm=get_groq_llm(),
        verbose=True,
        allow_delegation=False,
        max_rpm=None,
        max_iter=3,
    )

def create_optimizer_agent():
    """HVAC Optimization Engineer"""
    return Agent(
        role="HVAC Optimization Engineer",
        goal="Convert analytical insights into safe, explainable operational actions",
        backstory="Energy consultant who has optimized HVAC systems across 50+ commercial buildings",
        tools=[
            optimize_setpoints,
            recommend_chiller_sequencing,
            plan_load_shifting,
            score_maintenance_priority,
            compile_final_recommendations,
            store_recommendations_in_memory,
            query_similar_past_recommendations
        ],
        llm=get_groq_llm(),
        verbose=True,
        allow_delegation=False,
        max_rpm=None,
        max_iter=8,
    )

def create_reporter_agent():
    """Technical Report Writer"""
    return Agent(
        role="Technical Report Writer",
        goal="Produce a clear, complete, and actionable technical decision report",
        backstory="Engineering documentation specialist",
        tools=[
            generate_forecast_chart,
            generate_efficiency_trend_chart,
            generate_energy_heatmap,
            render_html_report,
            generate_pdf_report
        ],
        llm=get_groq_llm(),
        verbose=True,
        allow_delegation=False,
        max_rpm=None,
        max_iter=3,
        allow_code_execution=False,
    )

# ============================================================================
# SINGLETON INSTANCES (for backward compatibility)
# ============================================================================
ingestion_agent = create_ingestion_agent()
analyzer_agent = create_analyzer_agent()
forecast_agent = create_forecast_agent()
optimizer_agent = create_optimizer_agent()
reporter_agent = create_reporter_agent()