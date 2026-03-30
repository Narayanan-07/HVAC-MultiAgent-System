# tests/test_pipeline_api.py

import pytest
import httpx
import time

BASE_URL = "http://localhost:8000/api/v1"

@pytest.mark.skip(reason="Requires running server and valid Gemini API quota")

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