import json
import pandas as pd
import numpy as np
from prophet import Prophet
from xgboost import XGBRegressor
from crewai.tools import tool

@tool("Prophet Forecaster")
def run_prophet_forecast(data_json: str, horizon_hours: int) -> str:
    """
    Runs Prophet forecast on historical data. Minimum 168 rows required.
    Input: data_json (JSON string with timestamp, meter_reading, air_temperature, relative_humidity, is_weekend), horizon_hours
    Output: JSON string with forecast, mape_on_training, and peak_hours.
    """
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)
        
        if len(df) < 168:
            raise ValueError("Minimum 168 rows required for Prophet forecast.")
            
        if 'timestamp' in df.columns and 'electricity_kwh' in df.columns:
            df.rename(columns={'timestamp': 'ds', 'electricity_kwh': 'y'}, inplace=True)
            
        df['ds'] = pd.to_datetime(df['ds'])
        
        # Fit model
        model = Prophet(
            yearly_seasonality=True, 
            weekly_seasonality=True, 
            daily_seasonality=True, 
            seasonality_mode='multiplicative'
        )
        
        for reg in ['air_temperature', 'relative_humidity', 'is_weekend']:
            if reg in df.columns:
                model.add_regressor(reg)
                
        model.fit(df)
        
        future = model.make_future_dataframe(periods=horizon_hours, freq='h') # lowercase h is correct for newer pandas/prophet, but let's use 'h'
        
        # Future regressors simple fill
        for reg in ['air_temperature', 'relative_humidity', 'is_weekend']:
            if reg in df.columns:
                last_val = df[reg].iloc[-1]
                future[reg] = df[reg].tolist() + [last_val] * horizon_hours
            
        forecast = model.predict(future)
        future_forecast = forecast.tail(horizon_hours)
        
        forecast_list = []
        for _, row in future_forecast.iterrows():
            forecast_list.append({
                "ds": row['ds'].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "yhat": row['yhat'],
                "yhat_lower": row['yhat_lower'],
                "yhat_upper": row['yhat_upper']
            })
            
        yhat_90 = future_forecast['yhat'].quantile(0.9)
        peak_hours_df = future_forecast[future_forecast['yhat'] > yhat_90]
        peak_hours = []
        for _, row in peak_hours_df.iterrows():
            peak_hours.append(row['ds'].strftime("%Y-%m-%dT%H:%M:%SZ"))
            
        train_pred = model.predict(df)
        y_true = df['y']
        y_pred = train_pred['yhat']
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        result = {
            "model_used": "prophet",
            "horizon_hours": horizon_hours,
            "forecast": forecast_list,
            "mape_on_training": float(mape),
            "peak_hours": peak_hours
        }
        return json.dumps(result)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("XGBoost Forecaster")
def run_xgboost_forecast(data_json: str, horizon_hours: int) -> str:
    """
    Runs XGBoost forecast.
    Input: data_json, horizon_hours
    """
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)
        
        required_features = [
            'hour_of_day', 'day_of_week', 'month', 'is_weekend', 
            'airTemperature', 'relative_humidity', 'rolling_avg_24h',
            'lag_1h', 'lag_24h'
        ]
        
        for f in required_features:
            if f not in df.columns:
                df[f] = 0
                
        target = 'electricity_kwh'
        if target not in df.columns and 'y' in df.columns:
            target = 'y'
            
        X = df[required_features]
        y = df[target]
        
        model = XGBRegressor(n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42)
        model.fit(X, y)
        
        last_row = X.iloc[-1].copy()
        future_X = []
        
        for i in range(horizon_hours):
            new_row = last_row.copy()
            new_row['hour_of_day'] = (new_row['hour_of_day'] + i + 1) % 24
            future_X.append(new_row)
            
        future_df = pd.DataFrame(future_X)
        yhat = model.predict(future_df)
        
        forecast_list = []
        last_timestamp = pd.to_datetime(df['timestamp'].iloc[-1]) if 'timestamp' in df.columns else pd.to_datetime(df['ds'].iloc[-1]) if 'ds' in df.columns else pd.Timestamp.now()
        
        for i in range(horizon_hours):
            fut_ds = last_timestamp + pd.Timedelta(hours=i+1)
            pred_y = float(yhat[i])
            forecast_list.append({
                "ds": fut_ds.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "yhat": pred_y,
                "yhat_lower": pred_y * 0.9,
                "yhat_upper": pred_y * 1.1
            })
            
        yhat_90 = np.percentile(yhat, 90)
        peak_hours = []
        for i, val in enumerate(yhat):
            if val > yhat_90:
                fut_ds = last_timestamp + pd.Timedelta(hours=i+1)
                peak_hours.append(fut_ds.strftime("%Y-%m-%dT%H:%M:%SZ"))
                
        train_pred = model.predict(X)
        mape = np.mean(np.abs((y - train_pred) / y)) * 100
        
        result = {
            "model_used": "xgboost",
            "horizon_hours": horizon_hours,
            "forecast": forecast_list,
            "mape_on_training": float(mape),
            "peak_hours": peak_hours
        }
        return json.dumps(result)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("Peak Demand Predictor")
def predict_peak_demand_windows(forecast_json: str) -> str:
    """
    Parses forecast JSON to find continuous windows > 85th percentile.
    """
    try:
        data = json.loads(forecast_json)
        if "error" in data:
            return forecast_json
            
        forecast = data.get("forecast", [])
        if not forecast:
            return json.dumps([])
            
        yhats = [item['yhat'] for item in forecast]
        yhat_85 = np.percentile(yhats, 85)
        
        windows = []
        current_window = None
        
        for item in forecast:
            if item['yhat'] > yhat_85:
                if current_window is None:
                    current_window = {
                        "start_time": item['ds'],
                        "end_time": item['ds'],
                        "peak_yhat_kwh": item['yhat'],
                        "duration_hours": 1
                    }
                else:
                    current_window["end_time"] = item['ds']
                    current_window["duration_hours"] += 1
                    current_window["peak_yhat_kwh"] = max(current_window["peak_yhat_kwh"], item['yhat'])
            else:
                if current_window is not None:
                    current_window["pre_cool_recommendation"] = f"Pre-cool by {min(2, current_window['duration_hours'])} hours"
                    windows.append(current_window)
                    current_window = None
                    
        if current_window is not None:
             current_window["pre_cool_recommendation"] = f"Pre-cool by {min(2, current_window['duration_hours'])} hours"
             windows.append(current_window)
             
        return json.dumps(windows)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("Best Forecast Model Selector")
def select_best_forecast_model(data_json: str, horizon_hours: int) -> str:
    """
    Tries Prophet first, and falls back to XGBoost if insufficient data or error occurs.
    """
    prophet_result_str = run_prophet_forecast.func(data_json, horizon_hours)
    prophet_result = json.loads(prophet_result_str)
    
    if "error" not in prophet_result:
        return prophet_result_str
        
    xgb_result_str = run_xgboost_forecast.func(data_json, horizon_hours)
    xgb_result = json.loads(xgb_result_str)
    
    if "error" not in xgb_result:
        xgb_result["fallback_reason"] = prophet_result.get("error", "Unknown error with Prophet")
        return json.dumps(xgb_result)
        
    return json.dumps({
        "error": "Both Prophet and XGBoost failed", 
        "details": {"prophet": prophet_result, "xgboost": xgb_result}
    })
