import pytest
import pandas as pd
import json
import numpy as np
from backend.agents.tools.anomaly_tools import (
    detect_anomalies_isolation_forest,
    validate_anomalies_zscore,
    classify_root_cause,
    score_degradation_trend,
    generate_efficiency_scorecard
)

@pytest.fixture
def anomaly_data_json():
    np.random.seed(42)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2016-01-01", periods=100, freq="h").astype(str),
        "meter_reading": np.random.normal(100, 10, 100),
        "iKW_TR": np.random.normal(0.6, 0.05, 100),
        "air_temperature": np.random.normal(25, 2, 100),
        "relative_humidity": np.random.normal(60, 5, 100),
        "hour_of_day": np.random.randint(0, 24, 100),
        "is_weekend": np.zeros(100)
    })
    # Inject anomaly
    df.loc[50, "meter_reading"] = 500
    df.loc[50, "iKW_TR"] = 2.5
    return df.to_json(orient="records")

def test_detect_anomalies_isolation_forest(anomaly_data_json):
    # .run() for single arg tool
    res = json.loads(detect_anomalies_isolation_forest.run(anomaly_data_json))
    assert "anomaly_count" in res
    assert res["anomaly_count"] > 0

def test_validate_anomalies_zscore(anomaly_data_json):
    # .func() for multi arg tool
    res = json.loads(validate_anomalies_zscore.func(anomaly_data_json, "meter_reading"))
    assert len(res) > 0
    assert "timestamp" in res[0]
    assert "z_score" in res[0]
    assert res[0]["z_score"] > 3.0 or res[0]["z_score"] < -3.0

def test_classify_root_cause(anomaly_data_json):
    # .run()
    res = json.loads(classify_root_cause.run(anomaly_data_json))
    assert len(res) > 0
    assert "root_cause" in res[0]

def test_score_degradation_trend(anomaly_data_json):
    # .run()
    res = json.loads(score_degradation_trend.run(anomaly_data_json))
    assert "trend_status" in res
    assert "degradation_score" in res
    assert "30d_mean_ikwtr" in res

def test_generate_efficiency_scorecard(anomaly_data_json):
    # .run()
    res = json.loads(generate_efficiency_scorecard.run(anomaly_data_json))
    assert "efficiency_grade" in res
    assert "avg_ikwtr" in res