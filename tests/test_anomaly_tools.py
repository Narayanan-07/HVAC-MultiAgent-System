import pytest
import json
import pandas as pd
import numpy as np
from backend.agents.tools.anomaly_tools import (
    detect_anomalies_isolation_forest,
    validate_anomalies_zscore,
    classify_root_cause,
    score_degradation_trend
)

def test_isolation_forest_detects_injected_anomalies():
    """Inject obvious anomalies and verify detection"""
    # Create normal data
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        'timestamp': pd.date_range('2018-01-01', periods=n, freq='H'),
        'meter_reading': np.random.normal(100, 10, n),
        'iKW_TR': np.random.normal(0.60, 0.05, n),
        'air_temperature': np.random.normal(25, 3, n),
        'relative_humidity': np.random.normal(60, 5, n),
    })
    # Inject 10 obvious anomalies
    df.loc[50:59, 'iKW_TR'] = 2.5  # way above 0.60 benchmark
    
    result = json.loads(detect_anomalies_isolation_forest(df.to_json()))
    assert result['anomaly_count'] > 0
    assert result['anomaly_pct'] < 10  # contamination=0.05

def test_zscore_flags_outliers():
    """Z-score should flag values beyond 3 std"""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2018-01-01', periods=100, freq='H'),
        'iKW_TR': [0.60] * 99 + [5.0]  # last value is extreme outlier
    })
    result = json.loads(validate_anomalies_zscore(df.to_json(), 'iKW_TR'))
    assert len(result['flagged_rows']) >= 1
    assert result['flagged_rows'][0]['z_score'] > 3.0

def test_root_cause_equipment_driven():
    """High iKW-TR regardless of weather = equipment fault"""
    anomaly = {
        'air_temperature': 25.0,  # normal temp
        'air_temperature_zscore': 0.2,  # no deviation
        'iKW_TR': 0.92,  # very high = poor chiller
        'iKW_TR_zscore': 3.5,
        'hour_of_day': 3,
        'is_weekend': False
    }
    result = json.loads(classify_root_cause(json.dumps([anomaly])))
    assert result[0]['root_cause'] == 'EQUIPMENT-DRIVEN'

def test_degradation_score_range():
    """Degradation score must always be 0-100"""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2018-01-01', periods=720, freq='H'),
        'iKW_TR': np.random.normal(0.70, 0.05, 720)
    })
    result = json.loads(score_degradation_trend(df.to_json()))
    assert 0 <= result['degradation_score'] <= 100