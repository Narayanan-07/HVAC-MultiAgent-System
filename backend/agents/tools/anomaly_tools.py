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

        # NOTE: saved under a distinct name so it does NOT clobber the richer,
        # root-cause-classified anomalies that the report actually displays
        # (classify_root_cause writes {run_id}_anomalies.json).
        save_task_output(run_id, "anomalies_if", result)

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
def classify_root_cause(data_path: str, run_id: str = "unknown") -> str:
    """
    Detect and classify GENUINE HVAC anomalies for a single building.

    A point is treated as a real anomaly only when Isolation Forest flags it
    AND it is statistically extreme (|z| > 3) on a key variable — this avoids
    the "everything is 5% anomalous" artefact of contamination-only flagging.
    Each anomaly gets a specific, value-rich root cause. Saves
    {run_id}_anomalies.json as {"total_anomalies": N, "anomalies": [up to 10]}.
    """
    try:
        df = pd.read_csv(data_path)
        empty = {"total_anomalies": 0, "anomalies": []}
        if len(df) == 0:
            save_task_output(run_id, "anomalies", empty)
            return json.dumps({"total_anomalies": 0, "shown": 0})

        temp_col = 'airTemperature' if 'airTemperature' in df.columns else 'air_temperature'
        feats = [c for c in ['electricity_kwh', 'iKW_TR', temp_col, 'relative_humidity'] if c in df.columns]
        dfc = df.dropna(subset=feats).copy()
        if len(dfc) < 50 or 'iKW_TR' not in dfc.columns:
            save_task_output(run_id, "anomalies", empty)
            return json.dumps({"total_anomalies": 0, "shown": 0})

        # Multivariate flag (Isolation Forest)
        X = StandardScaler().fit_transform(dfc[feats])
        clf = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        dfc['if_pred'] = clf.fit_predict(X)

        # Univariate z-scores: legitimacy filter + classification signals
        dfc['ikwtr_z'] = zscore(dfc['iKW_TR'])
        dfc['temp_z'] = zscore(dfc[temp_col]) if temp_col in dfc.columns else 0.0
        dfc['elec_z'] = zscore(dfc['electricity_kwh']) if 'electricity_kwh' in dfc.columns else 0.0

        # A genuine anomaly: IF-flagged AND statistically extreme on a real axis
        # (|z| > 2.5 ≈ top ~0.6% tail — strict enough to be defensible, not the
        # contamination-forced 5% that made every building look identical).
        extreme = (dfc['ikwtr_z'].abs() > 2.5) | (dfc['temp_z'].abs() > 2.5) | (dfc['elec_z'].abs() > 2.5)
        anoms = dfc[(dfc['if_pred'] == -1) & extreme].copy()
        total = int(len(anoms))

        if total == 0:
            save_task_output(run_id, "anomalies", empty)
            return json.dumps({"total_anomalies": 0, "shown": 0})

        # Most severe first, then keep at most 10 (a small building may have fewer)
        anoms['sev_metric'] = anoms[['ikwtr_z', 'temp_z', 'elec_z']].abs().max(axis=1)
        anoms = anoms.sort_values('sev_metric', ascending=False).head(10)

        results = []
        for _, row in anoms.iterrows():
            ts = str(row.get('timestamp', 'Unknown'))
            ikwtr = float(row.get('iKW_TR', 0) or 0)
            tz, iz, ez = float(row['temp_z']), float(row['ikwtr_z']), float(row['elec_z'])
            temp = float(row.get(temp_col, 0) or 0)
            elec = float(row.get('electricity_kwh', 0) or 0)
            hour = int(row['hour_of_day']) if pd.notnull(row.get('hour_of_day')) else None
            wknd = bool(int(row['is_weekend'])) if pd.notnull(row.get('is_weekend')) else False

            if ikwtr > 0.85 or abs(iz) > 3:
                cause, sev, param = "Equipment degradation", "HIGH", "iKW-TR"
                desc = (f"Cooling efficiency spiked to {ikwtr:.2f} kW/TR (z={iz:+.1f}), well past the "
                        f"0.60 benchmark — likely fouled tubes, low refrigerant, or a failing compressor.")
            elif abs(tz) > 3 and abs(iz) < 2:
                cause, sev, param = "Weather driven", "MEDIUM", "Temperature"
                desc = (f"Ambient temperature reached {temp:.1f}°C (z={tz:+.1f}) while efficiency stayed "
                        f"normal — a load surge driven by outdoor conditions, not the plant.")
            elif abs(ez) > 3 and hour is not None and 9 <= hour <= 18 and not wknd:
                cause, sev, param = "Behavioral / occupancy", "MEDIUM", "Energy"
                desc = (f"Consumption reached {elec:.0f} kWh (z={ez:+.1f}) during business hours — an "
                        f"occupancy or equipment-usage spike rather than a fault.")
            elif abs(ez) > 3 and (wknd or hour is None or hour < 6 or hour > 21):
                cause, sev, param = "Scheduling / control", "MEDIUM", "Energy"
                desc = (f"High consumption ({elec:.0f} kWh, z={ez:+.1f}) outside occupied hours — a schedule "
                        f"or setpoint left running while the building is largely empty.")
            else:
                cause, sev, param = "Sensor / data quality", "LOW", "Multiple"
                desc = (f"Multivariate outlier (iKW-TR {ikwtr:.2f}, {temp:.1f}°C, {elec:.0f} kWh) with no single "
                        f"dominant driver — verify sensor calibration before acting.")

            results.append({
                "timestamp": ts, "parameter": param, "severity": sev, "root_cause": cause,
                "confidence": round(min(0.95, 0.6 + float(row['sev_metric']) / 12), 2),
                "description": desc,
            })

        save_task_output(run_id, "anomalies", {"total_anomalies": total, "anomalies": results})
        logger.info(f"✓ {total} genuine anomalies for {run_id}; reporting top {len(results)}")
        return json.dumps({"total_anomalies": total, "shown": len(results)})

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