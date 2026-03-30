from crewai import Task
from backend.agents.agent_definitions import (
    ingestion_agent,
    analyzer_agent,
    forecast_agent,
    optimizer_agent,
    reporter_agent
)

ingest_task = Task(
    description=(
        "Load the HVAC datasets from {dataset_path}, {weather_path}, {metadata_path}. "
        "Validate data quality. Engineer all features including iKW-TR derivation and WBT calculation. "
        "Return a JSON summary of the clean dataset."
    ),
    expected_output="JSON string containing: data_quality_report, processed_data_path, feature_summary, row_count, column_list",
    agent=ingestion_agent
)

analyze_task = Task(
    description=(
        "Using the clean dataset from Task 1, run Isolation Forest and Z-score anomaly detection. "
        "Classify root causes for all detected anomalies. Score the 30-day degradation trend. "
        "Generate the efficiency scorecard with iKW-TR grade."
    ),
    expected_output="JSON containing: anomaly_report, efficiency_scorecard, degradation_score, root_cause_summary",
    agent=analyzer_agent,
    context=[ingest_task]
)

forecast_task = Task(
    description=(
        "Generate {forecast_horizon_hours}-hour energy demand forecast for building at latitude {lat}, longitude {lon}. "
        "Fetch current weather forecast. Identify peak demand windows and pre-cooling opportunities."
    ),
    expected_output="JSON containing: forecast_24h, forecast_168h, peak_windows, model_used, mape",
    agent=forecast_agent,
    context=[ingest_task]
)

optimize_task = Task(
    description=(
        "Based on the anomaly analysis and energy forecast, generate the top optimization recommendations. "
        "Include setpoint adjustments, chiller sequencing, load shifting, and maintenance priority scoring. "
        "Query memory for past recommendations to avoid repetition."
    ),
    expected_output="JSON containing: ranked recommendations list (max 10), maintenance_priority, total_expected_savings_pct",
    agent=optimizer_agent,
    context=[analyze_task, forecast_task]
)

report_task = Task(
    description=(
        "Consolidate all agent outputs into a complete technical decision report. "
        "Generate all visualization charts. Render HTML report and convert to PDF. Save both files."
    ),
    expected_output="JSON containing: html_report_path, pdf_report_path, report_summary (executive summary text)",
    agent=reporter_agent,
    context=[ingest_task, analyze_task, forecast_task, optimize_task]
)
