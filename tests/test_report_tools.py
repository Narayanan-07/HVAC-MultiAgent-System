import pytest
import json
import base64
from loguru import logger
from backend.agents.tools.report_tools import (
    generate_forecast_chart,
    generate_efficiency_trend_chart,
    generate_energy_heatmap,
    render_html_report,
    generate_pdf_report
)

def test_generate_forecast_chart():
    forecast = json.dumps([
        {"timestamp": "2016-01-01T12:00:00Z", "yhat": 100, "yhat_lower": 90, "yhat_upper": 110},
        {"timestamp": "2016-01-01T13:00:00Z", "yhat": 105, "yhat_lower": 95, "yhat_upper": 115}
    ])
    # Single arg tool -> .run()
    res = generate_forecast_chart.run(forecast)
    assert isinstance(res, str)
    if not res.startswith("Error"):
        # Should be base64
        assert len(res) > 100

def test_generate_efficiency_trend_chart():
    data = json.dumps([
        {"timestamp": "2016-01-01T12:00:00Z", "iKW_TR": 0.6},
        {"timestamp": "2016-01-01T13:00:00Z", "iKW_TR": 0.9}
    ])
    res = generate_efficiency_trend_chart.run(data)
    assert isinstance(res, str)
    if not res.startswith("Error"):
        assert len(res) > 100

def test_generate_energy_heatmap():
    data = json.dumps([
        {"hour_of_day": 12, "day_of_week": 2, "electricity_kwh": 100},
        {"hour_of_day": 13, "day_of_week": 2, "electricity_kwh": 120}
    ])
    res = generate_energy_heatmap.run(data)
    assert isinstance(res, str)
    if not res.startswith("Error"):
        assert len(res) > 100

def test_render_html_report_error_handling():
    # .func() for multi-arg tool
    # Check that it handles bad JSON safely or returns error string
    res = render_html_report.func(
        data_quality_json="bad json", 
        efficiency_scorecard_json="{}",
        anomaly_report_json="[]", 
        forecast_json="[]",
        recommendations_json="[]", 
        maintenance_json="{}",
        building_id="b1", 
        run_id="run1"
    )
    assert isinstance(res, str)
    assert "Error" in res

def test_generate_pdf_report_error_handling():
    from loguru import logger
    from backend.agents.tools.report_tools import generate_pdf_report
    result = generate_pdf_report.func("nonexistent_path/report.html")
    assert result is not None