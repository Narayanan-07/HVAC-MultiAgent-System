import pytest
import json
import pandas as pd
import numpy as np
from backend.agents.tools.forecast_tools import (
    run_prophet_forecast, run_xgboost_forecast, predict_peak_demand_windows
)
from backend.agents.tools.weather_tools import fetch_weather_forecast

def make_sample_df(n_hours=720):
    """720 hours = 30 days"""
    np.random.seed(42)
    timestamps = pd.date_range('2018-01-01', periods=n_hours, freq='H')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'meter_reading': 100 + 30 * np.sin(np.arange(n_hours) * 2 * np.pi / 24) 
                         + np.random.normal(0, 5, n_hours),
        'air_temperature': 25 + 5 * np.sin(np.arange(n_hours) * 2 * np.pi / 24),
        'relative_humidity': np.random.normal(60, 10, n_hours).clip(20, 100),
        'is_weekend': [1 if pd.Timestamp(t).weekday() >= 5 else 0 for t in timestamps],
        'rolling_avg_24h': np.random.normal(100, 5, n_hours),
        'hour_of_day': [t.hour for t in timestamps],
        'day_of_week': [t.weekday() for t in timestamps],
        'month': [t.month for t in timestamps],
    })
    return df

def test_prophet_returns_correct_horizon():
    df = make_sample_df(720)
    result = json.loads(run_prophet_forecast(df.to_json(), 24))
    assert result['model_used'] == 'prophet'
    assert len(result['forecast']) == 24

def test_prophet_confidence_intervals():
    """yhat_lower <= yhat <= yhat_upper for all rows"""
    df = make_sample_df(720)
    result = json.loads(run_prophet_forecast(df.to_json(), 24))
    for row in result['forecast']:
        assert row['yhat_lower'] <= row['yhat'] <= row['yhat_upper'], \
            f"CI violated: {row}"

def test_xgboost_fallback_works():
    """XGBoost should work even with 48 rows (too few for Prophet)"""
    df = make_sample_df(48)
    result = json.loads(run_xgboost_forecast(df.to_json(), 24))
    assert result['model_used'] == 'xgboost'
    assert len(result['forecast']) == 24

def test_peak_detection_finds_peaks():
    df = make_sample_df(720)
    forecast = json.loads(run_prophet_forecast(df.to_json(), 168))
    peaks = json.loads(predict_peak_demand_windows(json.dumps(forecast)))
    assert isinstance(peaks, list)
    for peak in peaks:
        assert 'start_time' in peak
        assert 'pre_cool_recommendation' in peak

def test_weather_api_returns_structure():
    """Test Open-Meteo API (requires internet)"""
    result = json.loads(fetch_weather_forecast(13.08, 80.27, 3))
    assert 'hourly' in result
    assert len(result['hourly']) > 0
    assert 'temperature_2m' in result['hourly'][0]