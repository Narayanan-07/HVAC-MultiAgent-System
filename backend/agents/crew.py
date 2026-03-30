from crewai import Crew, Process
from backend.agents.agent_definitions import (
    ingestion_agent,
    analyzer_agent,
    forecast_agent,
    optimizer_agent,
    reporter_agent
)
from backend.agents.task_definitions import (
    ingest_task,
    analyze_task,
    forecast_task,
    optimize_task,
    report_task
)

def build_hvac_crew() -> Crew:
    return Crew(
        agents=[
            ingestion_agent,
            analyzer_agent,
            forecast_agent,
            optimizer_agent,
            reporter_agent
        ],
        tasks=[
            ingest_task,
            analyze_task,
            forecast_task,
            optimize_task,
            report_task
        ],
        process=Process.sequential,
        verbose=True,
        memory=True
    )
