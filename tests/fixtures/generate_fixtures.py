import pandas as pd
import numpy as np
from pathlib import Path
import datetime

def generate_fixtures():
    fixtures_dir = Path(__file__).parent
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate 30 days of hourly data (720 rows)
    np.random.seed(42)
    start_date = pd.Timestamp("2016-01-01 00:00:00", tz="UTC")
    timestamps = pd.date_range(start_date, periods=720, freq='h')
    
    # 1. sample_metadata.csv
    metadata = pd.DataFrame({
        "building_id": ["building_001"],
        "site_id": ["site_01"],
        "primaryspaceusage": ["office"],
        "sqm": [5000],
        "lat": [13.08],
        "lng": [80.27]
    })
    metadata.to_csv(fixtures_dir / "sample_metadata.csv", index=False)
    
    # 2. sample_weather.csv
    hours_from_start = (timestamps - timestamps[0]).components.hours + (timestamps - timestamps[0]).components.days * 24
    
    # Base temp around 25, sinusoidal variance ± 5, noise
    base_temp = 25
    daily_temp_variance = 5 * np.sin(2 * np.pi * (timestamps.hour - 6) / 24)
    temp_noise = np.random.normal(0, 0.5, 720)
    air_temp = base_temp + daily_temp_variance + temp_noise
    
    # Humidity
    rh = 60 + 15 * np.cos(2 * np.pi * (timestamps.hour - 6) / 24) + np.random.normal(0, 2, 720)
    rh = np.clip(rh, 30, 100)
    
    weather = pd.DataFrame({
        "timestamp": timestamps,
        "site_id": ["site_01"] * 720,
        "airTemperature": air_temp,
        "dewTemperature": air_temp - ((100 - rh) / 5), # approx dew point
        "cloudCoverage": np.random.randint(0, 8, 720),
        "precipDepth1HR": np.zeros(720)
    })
    weather.to_csv(fixtures_dir / "sample_weather.csv", index=False)
    
    # 3. sample_data.csv (raw meter data or processed data?)
    # "Generates sample_data.csv (720 rows, 30 days hourly)... sinusoidal load"
    base_load = 100
    occupancy_effect = np.where((timestamps.hour >= 8) & (timestamps.hour <= 18), 50, 0)
    weekend_effect = np.where(timestamps.dayofweek >= 5, -30, 0)
    
    # Sinusoidal daily curve
    daily_curve = 20 * np.sin(2 * np.pi * (timestamps.hour - 8) / 24)
    daily_curve = np.clip(daily_curve, 0, None)
    
    chilledwater_kwh = base_load + occupancy_effect + weekend_effect + daily_curve + np.random.normal(0, 5, 720)
    electricity_kwh = (chilledwater_kwh * 0.8) + 50 + np.random.normal(0, 5, 720)
    
    # also we need the features_final.csv schema according to dataset instructions
    sample_data = pd.DataFrame({
        "timestamp": timestamps,
        "building_id": ["building_001"] * 720,
        "site_id": ["site_01"] * 720,
        "building_type": ["office"] * 720,
        "chilledwater_kwh": chilledwater_kwh,
        "electricity_kwh": electricity_kwh,
        "airTemperature": air_temp,
        "dewTemperature": weather["dewTemperature"],
        "relative_humidity": rh,
        "wet_bulb_temp_c": air_temp - 3, # approx
        "iKW_TR": np.random.uniform(0.5, 1.2, 720),
        "hour_of_day": timestamps.hour,
        "day_of_week": timestamps.dayofweek,
        "month": timestamps.month,
        "is_weekend": (timestamps.dayofweek >= 5).astype(int),
        "rolling_avg_24h": pd.Series(electricity_kwh).rolling(24, min_periods=1).mean(),
        "load_category": ["medium"] * 720
    })
    
    # Make some anomalies for tests
    sample_data.loc[100, "electricity_kwh"] += 500 # anomaly
    sample_data.loc[200, "iKW_TR"] = 2.5 # efficiency anomaly
    
    sample_data.to_csv(fixtures_dir / "sample_data.csv", index=False)
    print("Fixtures generated.")

if __name__ == "__main__":
    generate_fixtures()
