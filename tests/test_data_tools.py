import pytest
import pandas as pd
import json
import numpy as np
import warnings
from pathlib import Path
from backend.agents.tools.data_tools import (
    load_and_prepare_data,
    handle_missing_values,
    derive_humidity_wbt_ikwtr,
    engineer_features,
    generate_quality_report
)
from backend.agents.tools.data_tools import derive_humidity_wbt_ikwtr, generate_quality_report

# Fixtures from generate_fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_load_and_prepare_errors():
    with pytest.raises(RuntimeError):
         load_and_prepare_data("/invalid/path")

def test_handle_missing_values():
    df = pd.DataFrame({
        "building_id": ["A", "A", "A"],
        "timestamp": pd.date_range("2016-01-01", periods=3, freq="h"),
        "electricity_kwh": [10, np.nan, 30],
        "airTemperature": [20, np.nan, 22]
    })
    cleaned = handle_missing_values(df)
    assert cleaned["electricity_kwh"].isna().sum() == 0
    assert cleaned["airTemperature"].isna().sum() == 0

def test_derive_humidity_wbt_ikwtr():
    df = pd.DataFrame({
        "airTemperature": [30.0],
        "dewTemperature": [20.0],
        "chilledwater_kwh": [150.0],
        "electricity_kwh": [100.0]
    })
    res = derive_humidity_wbt_ikwtr(df)
    assert "relative_humidity" in res.columns
    assert "wet_bulb_temp_c" in res.columns
    assert "iKW_TR" in res.columns
    assert np.isclose(res["relative_humidity"].iloc[0], 55.3, atol=2)

def test_engineer_features():
    df = pd.DataFrame({
        "building_id": ["A", "A"],
        "timestamp": pd.date_range("2016-01-01", periods=2, freq="h"),
        "electricity_kwh": [10, 20]
    })
    res = engineer_features(df)
    assert "hour_of_day" in res.columns
    assert "is_weekend" in res.columns
    assert "load_category" in res.columns

def test_generate_quality_report():
    df = pd.DataFrame({
        "building_id": ["A"],
        "timestamp": pd.date_range("2016-01-01", periods=1, freq="h"),
        "iKW_TR": [0.6],
        "val": [1]
    })
    rep = generate_quality_report(df)
    assert rep["quality_flag"] in ["PASS", "WARN", "FAIL"]
    assert "missing_pct" in rep


