# task_definitions.py
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
        "The data engineering pipeline has already successfully run in the background. "
        "Your ONLY task is to report this success and provide the path to the clean data for the next agents.\n\n"
        "LLAMA GUARD: For your final answer, return EXACTLY this JSON string and nothing else:\n"
        "{\n"
        "  \"data_quality_report\": \"PASS\",\n"
        "  \"processed_data_path\": \"{data_path}\",\n"
        "  \"feature_summary\": \"Single-building dataset ready for analysis\",\n"
        "  \"building_id\": \"{building_id}\",\n"
        "  \"column_list\": [\"timestamp\", \"building_id\", \"electricity_kwh\", \"iKW_TR\"]\n"
        "}"
    ),
    expected_output="JSON summary containing: data_quality_report, processed_data_path, feature_summary, row_count, column_list.",
    agent=ingestion_agent
)

analyze_task = Task(
    description=(
        "Analyze HVAC data for building '{building_id}' (run_id: {run_id}).\n\n"
        "Use '{data_path}' as data_path. This file contains ONLY this building's data.\n\n"
        "REQUIRED STEPS (in order), passing data_path='{data_path}' to each:\n"
        "1. Call 'generate_data_quality_report' with run_id='{run_id}'\n"
        "2. Call 'detect_anomalies_isolation_forest' with run_id='{run_id}'\n"
        "3. Call 'classify_root_cause' with run_id='{run_id}'\n"
        "4. Call 'generate_efficiency_scorecard' with run_id='{run_id}'\n"
        "5. Call 'score_degradation_trend' with run_id='{run_id}'\n\n"
        "Return a brief summary."
    ),
    expected_output="JSON summary with anomaly count and efficiency grade",
    agent=analyzer_agent,
    context=[ingest_task]
)

forecast_task = Task(
    description=(
        "Generate an energy demand forecast for building '{building_id}' (run_id {run_id}).\n\n"
        "CRITICAL: Pass run_id='{run_id}' to forecast tools.\n\n"
        "Call 'Best Forecast Model Selector' with data_path='{data_path}', "
        "horizon_hours={forecast_horizon_hours}, and run_id='{run_id}'."
    ),
    expected_output="JSON summary with model, mape",
    agent=forecast_agent,
    context=[ingest_task]
)

optimize_task = Task(
    description=(
        "Generate recommendations for run_id {run_id}.\n\n"
        "CRITICAL: Pass run_id='{run_id}' to compile_final_recommendations and score_maintenance_priority.\n\n"
        "Use optimization tools."
    ),
    expected_output="JSON with recommendations",
    agent=optimizer_agent,
    context=[analyze_task, forecast_task]
)

report_task = Task(
    description=(
        "Generate HTML and PDF reports in STRICT ORDER.\n\n"
        "STEP 1: Call 'Render HTML Report' tool with:\n"
        "  - run_id: {run_id}\n"
        "  - building_id: {building_id}\n"
        "Wait for the tool to return the HTML file path.\n\n"
        "STEP 2: Take the EXACT path returned from Step 1.\n"
        "Call 'PDF Report Generator' tool with:\n"
        "  - html_path: <the exact path from Step 1>\n"
        "  - run_id: {run_id}\n\n"
        "STEP 3: Return JSON:\n"
        "{{\n"
        "  \"html_path\": \"<path from Step 1>\",\n"
        "  \"pdf_path\": \"<path from Step 2>\",\n"
        "  \"status\": \"success\"\n"
        "}}\n\n"
        "DO NOT call both tools at the same time.\n"
        "DO NOT use placeholder paths like '/path/to/report.html'.\n"
        "USE THE ACTUAL RETURNED PATH."
    ),
    expected_output="JSON with actual file paths",
    agent=reporter_agent,
    context=[optimize_task]
)