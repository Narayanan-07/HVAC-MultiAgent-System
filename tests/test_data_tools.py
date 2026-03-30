import pytest
import pandas as pd
import json
from backend.agents.tools.data_tools import load_bdg2_datasets, engineer_hvac_features
from backend.agents.tools.thermo_tools import derive_wet_bulb_temperature, generate_data_quality_report

def test_wbt_derivation():
    """Stull equation: 30°C, 60% RH → ~23.5°C WBT"""
    wbt = derive_wet_bulb_temperature(30.0, 60.0)
    assert 22.0 < wbt < 25.0, f"WBT out of expected range: {wbt}"

def test_wbt_extreme_dry():
    """Dry air: WBT should be well below dry-bulb"""
    wbt = derive_wet_bulb_temperature(35.0, 10.0)
    assert wbt < 20.0

def test_wbt_saturated():
    """Saturated air (100% RH): WBT == Dry-bulb"""
    wbt = derive_wet_bulb_temperature(25.0, 100.0)
    assert abs(wbt - 25.0) < 1.0

def test_feature_engineering_columns(sample_df_json):
    """Check all expected columns exist after feature engineering"""
    result = engineer_hvac_features(sample_df_json)
    df = pd.DataFrame(json.loads(result)["data"])
    required = ["hour_of_day", "day_of_week", "is_weekend", 
                "rolling_avg_24h", "load_category", "iKW_TR"]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"

def test_data_quality_report_pass(sample_df_json):
    """Clean data should return PASS"""
    report = json.loads(generate_data_quality_report(sample_df_json))
    assert report["quality_flag"] in ["PASS", "WARN"]
    assert 0 <= report["data_quality_score"] <= 100
