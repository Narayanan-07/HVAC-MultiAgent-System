# backend/agents/tools/forecast_tools.py

import json
import pandas as pd
import numpy as np
from prophet import Prophet
from xgboost import XGBRegressor
from crewai.tools import tool
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def save_task_output(run_id: str, task_name: str, data):
    """Save forecast output"""
    import os
    import json
    output_dir = "data/task_outputs"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{run_id}_{task_name}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"💾 Saved {task_name} to {filepath}")
    

MAX_TRAINING_ROWS = 8760
PROPHET_TIMEOUT_SECONDS = 120
SAMPLE_STRATEGY = "recent"


def sample_data_for_forecasting(df: pd.DataFrame, max_rows: int = MAX_TRAINING_ROWS, strategy: str = "recent") -> pd.DataFrame:
    if len(df) <= max_rows:
        logger.debug(f"Dataset has {len(df)} rows, no sampling needed")
        return df
    
    logger.warning(f"Dataset has {len(df)} rows, sampling to {max_rows} for performance")
    
    if strategy == "recent":
        sampled = df.tail(max_rows).copy()
        logger.info(f"✂️ Using most recent {max_rows} rows ({len(df) - max_rows} rows skipped)")
    elif strategy == "stratified":
        step = len(df) // max_rows
        sampled = df.iloc[::step].copy()
        logger.info(f"✂️ Taking every {step}th row ({len(df) - len(sampled)} rows skipped)")
    else:
        sampled = df.sample(n=max_rows, random_state=42).sort_index()
        logger.info(f"✂️ Random sampling to {max_rows} rows")
    
    return sampled

@tool("Prophet Forecaster")
def run_prophet_forecast(data_path: str, horizon_hours: int) -> str:
    """Prophet forecast on sampled data"""
    logger.info(f"📊 Running Prophet forecast: {horizon_hours}h horizon")
    start_time = time.time()
    
    try:
        df = pd.read_csv(data_path)
        logger.debug(f"Loaded {len(df)} rows from {data_path}")
        
        df = sample_data_for_forecasting(df, max_rows=MAX_TRAINING_ROWS, strategy=SAMPLE_STRATEGY)
        
        if len(df) < 72:
            error_msg = f"Insufficient data: {len(df)} rows (need 72 minimum after sampling)"
            logger.warning(error_msg)
            return json.dumps({"error": error_msg})
        
        if 'timestamp' in df.columns and 'electricity_kwh' in df.columns:
            df = df.rename(columns={'timestamp': 'ds', 'electricity_kwh': 'y'})
        elif 'ds' not in df.columns or 'y' not in df.columns:
            return json.dumps({"error": "Missing required columns"})
        
        # FIX: Remove timezone properly
        df['ds'] = pd.to_datetime(df['ds'], errors='coerce', utc=False).dt.tz_localize(None)
        df = df.dropna(subset=['ds', 'y'])
        
        if len(df) < 72:
            return json.dumps({"error": f"After cleaning: {len(df)} rows (need 72)"})
        
        df = df.sort_values('ds').reset_index(drop=True)
        
        logger.debug("Initializing Prophet model...")
        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=True,
            seasonality_mode='additive',
            changepoint_prior_scale=0.05,
            interval_width=0.80,
            mcmc_samples=0,
            uncertainty_samples=100,
        )
        
        available_regressors = []
        for reg in ['airTemperature', 'relative_humidity']:
            if reg in df.columns:
                df[reg] = df[reg].fillna(df[reg].median())
                model.add_regressor(reg)
                available_regressors.append(reg)
                logger.debug(f"Added regressor: {reg}")
        
        logger.debug(f"Fitting Prophet on {len(df)} rows...")
        fit_start = time.time()
        
        try:
            model.fit(df[['ds', 'y'] + available_regressors])
            fit_duration = time.time() - fit_start
            logger.debug(f"✅ Model fitted in {fit_duration:.2f}s")
        except Exception as e:
            logger.error(f"Prophet fitting failed: {e}")
            return json.dumps({"error": f"Prophet fitting failed: {str(e)}"})
        
        if fit_duration > PROPHET_TIMEOUT_SECONDS:
            logger.warning(f"⚠️ Prophet took {fit_duration:.2f}s (>{PROPHET_TIMEOUT_SECONDS}s)")
        
        future = model.make_future_dataframe(periods=horizon_hours, freq='h')
        
        for reg in available_regressors:
            last_val = df[reg].iloc[-1]
            future[reg] = df[reg].tolist() + [last_val] * horizon_hours
        
        logger.debug("Generating forecast...")
        forecast = model.predict(future)
        future_forecast = forecast.tail(horizon_hours)
        
        forecast_list = []
        for _, row in future_forecast.iterrows():
            forecast_list.append({
                "ds": row['ds'].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "yhat": round(float(row['yhat']), 2),
                "yhat_lower": round(float(row['yhat_lower']), 2),
                "yhat_upper": round(float(row['yhat_upper']), 2)
            })
        
        yhat_90 = future_forecast['yhat'].quantile(0.9)
        peak_hours = [
            row['ds'].strftime("%Y-%m-%dT%H:%M:%SZ") 
            for _, row in future_forecast.iterrows() 
            if row['yhat'] > yhat_90
        ]
        
        train_pred = model.predict(df[['ds'] + available_regressors])
        y_true = df['y'].values[-1000:]
        y_pred = train_pred['yhat'].values[-1000:]
        
        mask = y_true != 0
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) if mask.sum() > 0 else float('inf')
        
        total_time = time.time() - start_time
        logger.info(f"✅ Prophet forecast complete in {total_time:.2f}s: MAPE={mape:.2f}%, {len(peak_hours)} peak hours")
        
        result = {
            "model_used": "prophet",
            "horizon_hours": horizon_hours,
            "forecast": forecast_list,
            "mape_on_training": round(mape, 2),
            "peak_hours": peak_hours,
        }
        
        return json.dumps(result)
        
    except Exception as e:
        error_msg = f"Prophet forecast failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return json.dumps({"error": error_msg})

@tool("XGBoost Forecaster")
def run_xgboost_forecast(data_path: str, horizon_hours: int) -> str:
    """Fast XGBoost forecast"""
    logger.info(f"📊 Running XGBoost forecast: {horizon_hours}h horizon")
    start_time = time.time()
    
    try:
        df = pd.read_csv(data_path)
        original_len = len(df)
        df = sample_data_for_forecasting(df, max_rows=MAX_TRAINING_ROWS, strategy="recent")
        
        if len(df) < 24:
            return json.dumps({"error": f"Insufficient data: {len(df)} rows"})
        
        required_features = [
            'hour_of_day', 'day_of_week', 'month', 'is_weekend',
            'airTemperature', 'relative_humidity'
        ]
        
        for f in required_features:
            if f not in df.columns:
                df[f] = 0
        
        target = 'electricity_kwh' if 'electricity_kwh' in df.columns else 'y'
        if target not in df.columns:
            return json.dumps({"error": f"Target '{target}' not found"})
        
        X = df[required_features].fillna(0)
        # FIX: Pandas 3.x compatibility
        y = df[target].ffill().fillna(0)
        
        logger.debug("Training XGBoost...")
        model = XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
            tree_method='hist'
        )
        
        fit_start = time.time()
        model.fit(X, y)
        fit_duration = time.time() - fit_start
        logger.debug(f"Model trained in {fit_duration:.2f}s")
        
        last_row = X.iloc[-1].to_dict()
        future_X = []
        
        for i in range(horizon_hours):
            new_row = last_row.copy()
            new_row['hour_of_day'] = (last_row['hour_of_day'] + i + 1) % 24
            future_X.append(new_row)
        
        future_df = pd.DataFrame(future_X)
        yhat = model.predict(future_df)
        
        if 'timestamp' in df.columns:
            last_ts = pd.to_datetime(df['timestamp'].iloc[-1], utc=False).tz_localize(None) if pd.api.types.is_datetime64_any_dtype(df['timestamp']) else pd.to_datetime(df['timestamp'].iloc[-1])
        elif 'ds' in df.columns:
            last_ts = pd.to_datetime(df['ds'].iloc[-1], utc=False).tz_localize(None) if pd.api.types.is_datetime64_any_dtype(df['ds']) else pd.to_datetime(df['ds'].iloc[-1])
        else:
            last_ts = pd.Timestamp.now().tz_localize(None)
        
        forecast_list = []
        for i in range(horizon_hours):
            fut_ds = last_ts + pd.Timedelta(hours=i+1)
            pred_y = float(yhat[i])
            forecast_list.append({
                "ds": fut_ds.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "yhat": round(pred_y, 2),
                "yhat_lower": round(pred_y * 0.9, 2),
                "yhat_upper": round(pred_y * 1.1, 2)
            })
        
        yhat_90 = np.percentile(yhat, 90)
        peak_hours = [
            (last_ts + pd.Timedelta(hours=i+1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            for i, val in enumerate(yhat) if val > yhat_90
        ]
        
        train_pred = model.predict(X[-1000:])
        y_recent = y.values[-1000:]
        mask = y_recent != 0
        mape = float(np.mean(np.abs((y_recent[mask] - train_pred[mask]) / y_recent[mask])) * 100) if mask.sum() > 0 else float('inf')
        
        total_time = time.time() - start_time
        logger.info(f"✅ XGBoost complete in {total_time:.2f}s: MAPE={mape:.2f}%")
        
        result = {
            "model_used": "xgboost",
            "horizon_hours": horizon_hours,
            "forecast": forecast_list,
            "mape_on_training": round(mape, 2),
            "peak_hours": peak_hours,
        }
        
        return json.dumps(result)
        
    except Exception as e:
        return json.dumps({"error": f"XGBoost failed: {str(e)}"})

@tool("Peak Demand Predictor")
def predict_peak_demand_windows(forecast_json: str) -> str:
    """Find continuous peak windows"""
    try:
        data = json.loads(forecast_json)
        
        # Handle both formats: full object or just forecast array
        if isinstance(data, list):
            # Agent passed forecast array directly
            forecast = data
        elif isinstance(data, dict):
            # Check for error first
            if "error" in data:
                return forecast_json
            # Get forecast array
            forecast = data.get("forecast", [])
        else:
            return json.dumps({"error": "Invalid input format"})
        
        if not forecast:
            return json.dumps([])
        
        # Extract yhat values
        yhats = [item.get('yhat', 0) for item in forecast if isinstance(item, dict)]
        
        if not yhats:
            return json.dumps([])
        
        yhat_85 = np.percentile(yhats, 85)
        
        windows = []
        current_window = None
        
        for item in forecast:
            if not isinstance(item, dict):
                continue
                
            yhat_val = item.get('yhat', 0)
            
            if yhat_val > yhat_85:
                if current_window is None:
                    current_window = {
                        "start_time": item.get('ds', 'Unknown'),
                        "end_time": item.get('ds', 'Unknown'),
                        "peak_yhat_kwh": yhat_val,
                        "duration_hours": 1
                    }
                else:
                    current_window["end_time"] = item.get('ds', 'Unknown')
                    current_window["duration_hours"] += 1
                    current_window["peak_yhat_kwh"] = max(current_window["peak_yhat_kwh"], yhat_val)
            else:
                if current_window:
                    current_window["pre_cool_recommendation"] = f"Pre-cool by {min(2, current_window['duration_hours'])} hours"
                    windows.append(current_window)
                    current_window = None
        
        if current_window:
            current_window["pre_cool_recommendation"] = f"Pre-cool by {min(2, current_window['duration_hours'])} hours"
            windows.append(current_window)
        
        return json.dumps(windows)
    except Exception as e:
        logger.error(f"Peak demand prediction failed: {e}")
        return json.dumps({"error": str(e)})
    
@tool("Best Forecast Model Selector")
def select_best_forecast_model(data_path: str, horizon_hours: int, run_id: str = "unknown") -> str:
    """Try Prophet, fallback to XGBoost"""
    logger.info(f"🎯 Selecting best model for {horizon_hours}h...")
    
    prophet_result_str = run_prophet_forecast.func(data_path, horizon_hours)
    prophet_result = json.loads(prophet_result_str)
    
    if "error" not in prophet_result:
        logger.info("✅ Prophet successful")
        save_task_output(run_id, "forecast", prophet_result)
        return json.dumps(prophet_result)
    
    logger.warning(f"Prophet failed, trying XGBoost...")
    xgb_result_str = run_xgboost_forecast.func(data_path, horizon_hours)
    xgb_result = json.loads(xgb_result_str)
    
    if "error" not in xgb_result:
        logger.info("✅ XGBoost successful (fallback)")
        xgb_result["fallback_reason"] = prophet_result.get("error")
        save_task_output(run_id, "forecast", xgb_result)
        return json.dumps(xgb_result)
    
    return json.dumps({
        "error": "Both models failed",
        "details": {
            "prophet": prophet_result.get("error"),
            "xgboost": xgb_result.get("error")
        }
    })