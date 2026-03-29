from crewai import Agent
from backend.llm import llm 
from backend.agents.tools.anomaly_tools import (
    detect_anomalies_isolation_forest,
    validate_anomalies_zscore,
    classify_root_cause,
    score_degradation_trend,
    generate_efficiency_scorecard
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
