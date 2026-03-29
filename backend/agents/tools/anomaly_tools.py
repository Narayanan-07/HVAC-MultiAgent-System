import json
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy.stats import zscore
from crewai.tools import tool

logger = logging.getLogger(__name__)

@tool("detect_anomalies_isolation_forest")
def detect_anomalies_isolation_forest(data_json: str) -> str:
    """
    Detect anomalies in HVAC data using Isolation Forest.
    Input: JSON string of HVAC data containing ['meter_reading', 'iKW_TR', 'air_temperature', 'relative_humidity'].
    Returns: JSON string with anomaly_count, anomaly_pct, and anomaly_timestamps.
    """
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)
        
        features = ['meter_reading', 'iKW_TR', 'air_temperature', 'relative_humidity']
        # Check if features exist
        missing = [f for f in features if f not in df.columns]
        if missing:
            return json.dumps({"error": f"Missing features: {missing}"})
            
        df_clean = df.dropna(subset=features).copy()
        if len(df_clean) == 0:
            return json.dumps({"error": "No valid data after dropping NaNs."})
            
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_clean[features])
        
        clf = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        preds = clf.fit_predict(X_scaled)
        
        df_clean['anomaly_if'] = (preds == -1).astype(int)
        
        anomalies = df_clean[df_clean['anomaly_if'] == 1]
        
        result = {
            "anomaly_count": len(anomalies),
            "anomaly_pct": float(len(anomalies) / len(df_clean) * 100) if len(df_clean) > 0 else 0.0,
            "anomaly_timestamps": anomalies['timestamp'].tolist() if 'timestamp' in anomalies.columns else []
        }
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in detect_anomalies_isolation_forest: {e}")
        return json.dumps({"error": str(e)})

@tool("validate_anomalies_zscore")
def validate_anomalies_zscore(data_json: str, column: str) -> str:
    """
    Validate anomalies for a specific column using Z-score.
    Input: data_json (JSON string of data), column (string name of the column).
    Returns: JSON string containing a list of flagged rows (|Z| > 3.0) with timestamp, value, and z_score.
    """
    try:
        df = pd.DataFrame(json.loads(data_json))
        if column not in df.columns:
            return json.dumps({"error": f"Column {column} not found in the data."})
            
        df_clean = df.dropna(subset=[column]).copy()
        if len(df_clean) == 0:
            return json.dumps({"error": "No valid data for the specified column."})
            
        df_clean[f'z_score_{column}'] = zscore(df_clean[column])
        df_clean[f'anomaly_z_{column}'] = (df_clean[f'z_score_{column}'].abs() > 3.0).astype(int)
        
        anomalies = df_clean[df_clean[f'anomaly_z_{column}'] == 1]
        
        result = []
        for _, row in anomalies.iterrows():
            result.append({
                "timestamp": row.get('timestamp', 'Unknown'),
                "value": row[column],
                "z_score": float(row[f'z_score_{column}'])
            })
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in validate_anomalies_zscore: {e}")
        return json.dumps({"error": str(e)})

@tool("classify_root_cause")
def classify_root_cause(anomaly_data_json: str) -> str:
    """
    Classify root cause for anomalies based on specific rules.
    Input: JSON string of anomaly rows.
    Returns: JSON string with list of {timestamp, root_cause, confidence, description}.
    """
    try:
        df = pd.DataFrame(json.loads(anomaly_data_json))
        if len(df) == 0:
            return json.dumps([])
            
        if 'temp_z' not in df.columns and 'air_temperature' in df.columns:
            df['temp_z'] = zscore(df['air_temperature'].fillna(df['air_temperature'].mean()))
        elif 'temp_z' not in df.columns:
            df['temp_z'] = 0.0

        if 'ikwtr_z' not in df.columns and 'iKW_TR' in df.columns:
            df['ikwtr_z'] = zscore(df['iKW_TR'].fillna(df['iKW_TR'].mean()))
        elif 'ikwtr_z' not in df.columns:
            df['ikwtr_z'] = 0.0
            
        results = []
        for _, row in df.iterrows():
            timestamp = row.get('timestamp', 'Unknown')
            ikwtr = row.get('iKW_TR', 0)
            temp_z = row.get('temp_z', 0)
            ikwtr_z = row.get('ikwtr_z', 0)
            
            hour = row.get('hour_of_day')
            is_weekend = row.get('is_weekend')
            
            if hour is None or is_weekend is None:
                if timestamp != 'Unknown':
                    try:
                        dt = pd.to_datetime(timestamp)
                        hour = dt.hour
                        is_weekend = 1 if dt.weekday() >= 5 else 0
                    except:
                        hour = 12
                        is_weekend = 0
            
            # Note: is_weekend is sometimes a float/int, we cast to bool or compare
            is_wknd = bool(int(is_weekend) if pd.notnull(is_weekend) else 0)
            hr = int(hour) if pd.notnull(hour) else 12

            root_cause = "UNKNOWN"
            confidence = 0.5
            description = "Anomaly detected but root cause could not be confidently determined."
            
            if ikwtr > 0.85:
                root_cause = "EQUIPMENT-DRIVEN"
                confidence = 0.9
                description = f"High cooling energy intensity (iKW/TR = {ikwtr:.2f}) indicates potential equipment degradation or failure."
            elif abs(temp_z) > 2.0 and abs(ikwtr_z) < 1.0:
                root_cause = "WEATHER-DRIVEN"
                confidence = 0.85
                description = "Extreme ambient temperatures are driving up load without significant cooling efficiency loss."
            elif not is_wknd and (9 <= hr <= 18) and abs(temp_z) <= 2.0:
                root_cause = "BEHAVIORAL"
                confidence = 0.75
                description = "High load during standard operating hours suggests occupancy or behavioral demand spikes."
                
            results.append({
                "timestamp": timestamp,
                "root_cause": root_cause,
                "confidence": confidence,
                "description": description
            })
            
        return json.dumps(results)
    except Exception as e:
        logger.error(f"Error in classify_root_cause: {e}")
        return json.dumps({"error": str(e)})

@tool("score_degradation_trend")
def score_degradation_trend(data_json: str) -> str:
    """
    Score the degradation trend of the HVAC system over 7-day and 30-day windows.
    Input: JSON string of HVAC data containing timestamp and iKW_TR.
    Returns: JSON string with trend_status, degradation_score, 7d_mean_ikwtr, 30d_mean_ikwtr, benchmark.
    """
    try:
        df = pd.DataFrame(json.loads(data_json))
        if 'iKW_TR' not in df.columns or 'timestamp' not in df.columns:
            return json.dumps({"error": "Missing iKW_TR or timestamp."})
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').dropna(subset=['iKW_TR'])
        if len(df) == 0:
            return json.dumps({"error": "No valid iKW_TR data."})
            
        max_date = df['timestamp'].max()
        mask_7d = df['timestamp'] >= (max_date - pd.Timedelta(days=7))
        mask_30d = df['timestamp'] >= (max_date - pd.Timedelta(days=30))
        
        mean_7d = float(df[mask_7d]['iKW_TR'].mean()) if mask_7d.sum() > 0 else 0.0
        mean_30d = float(df[mask_30d]['iKW_TR'].mean()) if mask_30d.sum() > 0 else 0.0
        
        benchmark = 0.60
        trend_status = "stable"
        
        if mean_30d > benchmark * 1.10:
            trend_status = "degrading"
        elif mean_30d < benchmark * 0.95:
            trend_status = "improving"
            
        score = min(100.0, max(0.0, ((mean_30d - benchmark) / benchmark) * 100.0))
        
        result = {
            "trend_status": trend_status,
            "degradation_score": float(round(score, 2)),
            "7d_mean_ikwtr": float(round(mean_7d, 4)),
            "30d_mean_ikwtr": float(round(mean_30d, 4)),
            "benchmark": float(benchmark)
        }
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in score_degradation_trend: {e}")
        return json.dumps({"error": str(e)})

@tool("generate_efficiency_scorecard")
def generate_efficiency_scorecard(data_json: str) -> str:
    """
    Generate an efficiency scorecard based on iKW_TR values.
    Input: JSON string of HVAC data containing iKW_TR.
    Returns: JSON string with avg_ikwtr, min_ikwtr, max_ikwtr, pct_time_above_benchmark, and efficiency_grade.
    """
    try:
        df = pd.DataFrame(json.loads(data_json))
        if 'iKW_TR' not in df.columns:
            return json.dumps({"error": "Missing iKW_TR column."})
            
        ikwtr = df['iKW_TR'].dropna()
        if len(ikwtr) == 0:
            return json.dumps({"error": "No valid iKW_TR data."})
            
        avg_ikwtr = float(ikwtr.mean())
        min_ikwtr = float(ikwtr.min())
        max_ikwtr = float(ikwtr.max())
        
        benchmark = 0.60
        pct_above = float((ikwtr > benchmark).sum() / len(ikwtr) * 100.0)
        
        if avg_ikwtr < 0.55:
            grade = "A"
        elif avg_ikwtr < 0.65:
            grade = "B"
        elif avg_ikwtr < 0.75:
            grade = "C"
        elif avg_ikwtr <= 0.85:
            grade = "D"
        else:
            grade = "F"
            
        result = {
            "avg_ikwtr": round(avg_ikwtr, 4),
            "min_ikwtr": round(min_ikwtr, 4),
            "max_ikwtr": round(max_ikwtr, 4),
            "pct_time_above_benchmark": round(pct_above, 2),
            "efficiency_grade": grade
        }
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in generate_efficiency_scorecard: {e}")
        return json.dumps({"error": str(e)})
