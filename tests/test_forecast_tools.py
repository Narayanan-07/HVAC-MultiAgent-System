import pytest
import pandas as pd
import json
import numpy as np
from backend.agents.tools.forecast_tools import (
    run_prophet_forecast,
    run_xgboost_forecast,
    predict_peak_demand_windows,
    select_best_forecast_model
)

@pytest.fixture
def forecast_data_json():
    # Needs at least 168 rows for Prophet
    np.random.seed(42)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2016-01-01", periods=200, freq="h").astype(str),
        "electricity_kwh": np.random.normal(100, 10, 200),
        "air_temperature": np.random.normal(25, 2, 200),
        "relative_humidity": np.random.normal(60, 5, 200),
        "is_weekend": np.zeros(200),
        "hour_of_day": np.random.randint(0, 24, 200),
        "day_of_week": np.random.randint(0, 7, 200),
        "month": np.ones(200),
        "rolling_avg_24h": np.random.normal(100, 5, 200),
        "lag_1h": np.random.normal(100, 10, 200),
        "lag_24h": np.random.normal(100, 10, 200)
    })
    return df.to_json(orient="records")

def test_run_prophet_forecast(forecast_data_json):
    # .func() for multi-arg tool
    res = json.loads(run_prophet_forecast.func(forecast_data_json, 24))
    assert "forecast" in res
    assert len(res["forecast"]) == 24
    assert "mape_on_training" in res

def test_run_xgboost_forecast(forecast_data_json):
    # .func() for multi-arg tool
    res = json.loads(run_xgboost_forecast.func(forecast_data_json, 24))
    assert "forecast" in res
    assert len(res["forecast"]) == 24
    assert "mape_on_training" in res

def test_predict_peak_demand_windows():
    # Mocking a forecast output with one peak
    forecast_mock = {
        "forecast": [
            {"ds": "2016-01-01T12:00:00Z", "yhat": 50},
            {"ds": "2016-01-01T13:00:00Z", "yhat": 150}, # peak
            {"ds": "2016-01-01T14:00:00Z", "yhat": 60}
        ]
    }
    # .run() for single-arg tool
    res = json.loads(predict_peak_demand_windows.run(json.dumps(forecast_mock)))
    assert isinstance(res, list)

def test_select_best_forecast_model(forecast_data_json):
    # .func() for multi-arg tool
    res = json.loads(select_best_forecast_model.func(forecast_data_json, 12))
    assert "forecast" in res
    assert len(res["forecast"]) == 12
    assert "model_used" in res