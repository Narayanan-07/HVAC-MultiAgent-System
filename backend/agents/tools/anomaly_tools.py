import json
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy.stats import zscore
from crewai.tools import tool

logger = logging.getLogger(__name__)

def save_task_output(run_id: str, task_name: str, data):
    """Save task output to file for report generation"""
    import os
    import json
    output_dir = "data/task_outputs"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{run_id}_{task_name}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"💾 Saved {task_name} to {filepath}")
    
@tool("detect_anomalies_isolation_forest")
def detect_anomalies_isolation_forest(data_path: str, run_id: str = "unknown") -> str:
    """
    Detect anomalies in HVAC data using Isolation Forest.
    Input: data_path (Path to the clean CSV file).
    Returns: JSON string with anomaly_count, anomaly_pct, and limited sample timestamps.
    """
    try:
        df = pd.read_csv(data_path)
        
        # Use columns present in engineered data
        features = ['electricity_kwh', 'iKW_TR', 'airTemperature', 'relative_humidity']
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
        
        # Limit timestamps to 10 to save tokens under Groq's small TPM limits
        timestamps = anomalies['timestamp'].tolist() if 'timestamp' in anomalies.columns else []
        
        result = {
            "anomaly_count": len(anomalies),
            "anomaly_pct": float(len(anomalies) / len(df_clean) * 100) if len(df_clean) > 0 else 0.0,
            "anomaly_timestamps": timestamps[:10],
            "note": "Timestamps limited to top 10 to conserve context tokens."
        }
        
        save_task_output(run_id, "anomalies", result)
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in detect_anomalies_isolation_forest: {e}")
        return json.dumps({"error": str(e)})

@tool("validate_anomalies_zscore")
def validate_anomalies_zscore(data_path: str, column: str) -> str:
    """
    Validate anomalies for a specific column using Z-score.
    Input: data_path (CSV path), column (string name of the column).
    Returns: JSON string containing top 10 flagged rows.
    """
    try:
        df = pd.read_csv(data_path)
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
        return json.dumps(result[:10])
    except Exception as e:
        logger.error(f"Error in validate_anomalies_zscore: {e}")
        return json.dumps({"error": str(e)})

@tool("classify_root_cause")
def classify_root_cause(data_path: str,run_id: str = "unknown") -> str:
    """
    Classify root cause for anomalies based on specific rules.
    Input: data_path (CSV path), run_id (run identifier).
    Returns: JSON string with list of {timestamp, root_cause, confidence, description}.
    """
    try:
        df = pd.read_csv(data_path)
        if len(df) == 0:
            return json.dumps([])
            
        # Determine column for temperature
        temp_col = 'airTemperature' if 'airTemperature' in df.columns else 'air_temperature'
        if temp_col in df.columns:
            df['temp_z'] = zscore(df[temp_col].fillna(df[temp_col].mean()))
        else:
            df['temp_z'] = 0.0

        if 'iKW_TR' in df.columns:
            df['ikwtr_z'] = zscore(df['iKW_TR'].fillna(df['iKW_TR'].mean()))
        else:
            df['ikwtr_z'] = 0.0
            
        # Select top 20 most extreme data points based on z-scores to classify
        df['anomaly_score'] = df['temp_z'].abs() + df['ikwtr_z'].abs()
        anomalies = df.sort_values(by='anomaly_score', ascending=False).head(20)
            
        results = []
        for _, row in anomalies.iterrows():
            timestamp = row.get('timestamp', 'Unknown')
            ikwtr = row.get('iKW_TR', 0)
            temp_z = row.get('temp_z', 0)
            ikwtr_z = row.get('ikwtr_z', 0)
            
            hour = row.get('hour_of_day')
            is_weekend = row.get('is_weekend')
            
            if hour is None or is_weekend is None:
                if timestamp != 'Unknown':
                    try:
                        # Safely remove tz info if present to allow .hour extraction safely
                        dt = pd.to_datetime(timestamp, utc=True).tz_localize(None)
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
            
            # ====================================================================
            # EXISTING LOGIC - KEPT INTACT
            # ====================================================================
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
            
            # ====================================================================
            # ADDED: 3 fields needed by template + severity logic
            # ====================================================================
            # Determine severity based on iKW-TR value and z-scores
            if ikwtr > 1.2 or abs(temp_z) > 3 or abs(ikwtr_z) > 3:
                severity = "HIGH"
            elif ikwtr > 0.9 or abs(temp_z) > 2 or abs(ikwtr_z) > 2:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            # Determine primary parameter
            if ikwtr > 0.85:
                parameter = "iKW_TR"
            elif abs(temp_z) > abs(ikwtr_z):
                parameter = "Temperature"
            else:
                parameter = "Multiple"
            
            results.append({
                "timestamp": str(timestamp),  # Ensure string format
                "parameter": parameter,  # ← ADDED (required by template)
                "severity": severity,    # ← ADDED (required by template)
                "root_cause": root_cause,
                "confidence": confidence,
                "description": description
            })
        
        # ====================================================================
        # ADDED: Save to file so reporter can load it
        # ====================================================================
        save_task_output(run_id, "anomalies", results)
        
        logger.info(f"✓ Classified {len(results)} anomalies with root causes")
        return json.dumps(results)
        
    except Exception as e:
        logger.error(f"Error in classify_root_cause: {e}")
        return json.dumps({"error": str(e)})

@tool("generate_data_quality_report")
def generate_data_quality_report(data_path: str) -> str:
    """
    Generate data quality scorecard for all columns.
    """
    try:
        df = pd.read_csv(data_path)
        total_rows = len(df)
        
        quality_report = []
        
        # Check key columns
        for col in ['timestamp', 'electricity_kwh', 'iKW_TR', 'airTemperature', 'relative_humidity']:
            if col not in df.columns:
                continue
            
            missing = df[col].isna().sum()
            completeness = ((total_rows - missing) / total_rows * 100) if total_rows > 0 else 0
            
            if completeness >= 95:
                flag = "EXCELLENT"
            elif completeness >= 80:
                flag = "GOOD"
            elif completeness >= 60:
                flag = "FAIR"
            else:
                flag = "POOR"
            
            quality_report.append({
                "column": col,
                "completeness": round(completeness, 1),
                "quality_flag": flag
            })
        
        # Save
        save_task_output("data_quality", quality_report)
        
        logger.info(f"Generated data quality report with {len(quality_report)} columns")
        return json.dumps(quality_report)
        
    except Exception as e:
        logger.error(f"Data quality error: {e}")
        return json.dumps({"error": str(e)})

@tool("score_degradation_trend")
def score_degradation_trend(data_path: str) -> str:
    """
    Score the degradation trend of the HVAC system over 7-day and 30-day windows.
    Input: data_path (CSV path).
    Returns: JSON summary of iKW-TR trends.
    """
    try:
        df = pd.read_csv(data_path)
        if 'iKW_TR' not in df.columns or 'timestamp' not in df.columns:
            return json.dumps({"error": "Missing iKW_TR or timestamp."})
            
        # Convert to UTC and strip timezone
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
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

@tool("generate_data_quality_report")
def generate_data_quality_report(data_path: str, run_id: str = "unknown") -> str:  # ← ADD run_id parameter
    """
    Generate data quality scorecard for key columns and save to a run-specific file.
    Input: data_path (CSV path), run_id (the current run identifier).
    Returns: JSON list with column completeness.
    """
    try:
        df = pd.read_csv(data_path)
        total_rows = len(df)
        
        quality_report = []
        
        # Check key columns only
        key_columns = ['timestamp', 'electricity_kwh', 'iKW_TR', 'airTemperature', 'relative_humidity']
        
        for col in key_columns:
            if col not in df.columns:
                continue
            
            missing = df[col].isna().sum()
            completeness = ((total_rows - missing) / total_rows * 100) if total_rows > 0 else 0
            
            # Assign quality flag
            if completeness >= 95:
                flag = "EXCELLENT"
            elif completeness >= 80:
                flag = "GOOD"
            elif completeness >= 60:
                flag = "FAIR"
            else:
                flag = "POOR"
            
            quality_report.append({
                "column": col,
                "completeness": round(completeness, 1),
                "quality_flag": flag
            })
        
        # Save to file using the provided run_id
        save_task_output(run_id, "data_quality", quality_report)  # ← FIX: Pass run_id here
        
        logger.info(f"✓ Generated data quality report for {len(quality_report)} columns for run {run_id}")
        return json.dumps(quality_report)
        
    except Exception as e:
        logger.error(f"Data quality report error: {e}")
        return json.dumps({"error": str(e)})

@tool("generate_efficiency_scorecard")
def generate_efficiency_scorecard(data_path: str, run_id: str = "unknown") -> str:  # ADD run_id parameter
    """Generate efficiency scorecard and SAVE to file"""
    try:
        df = pd.read_csv(data_path)
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
        
        # SAVE TO FILE
        save_task_output(run_id, "efficiency", result)
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in generate_efficiency_scorecard: {e}")
        return json.dumps({"error": str(e)})