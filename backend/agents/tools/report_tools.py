import json
import os
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from crewai.tools import tool
from loguru import logger

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
from jinja2 import Environment, FileSystemLoader
import base64

# ============================================================================
# IMPACT QUANTIFICATION
# ============================================================================
# Tariff and emission factor are assumptions surfaced in the report footnote;
# override via env for a different region.
TARIFF_PER_KWH = float(os.getenv("HVAC_TARIFF_PER_KWH", "8.0"))
CURRENCY = os.getenv("HVAC_CURRENCY", "₹")  # default Indian Rupee
CO2_KG_PER_KWH = 0.71
# Grade -> estimated optimization potential (%). Bounded to ranges supported by
# the AI-HVAC literature (single-digit for already-efficient sites up to ~30%).
GRADE_SAVINGS = {"A": 6, "B": 10, "C": 15, "D": 22, "F": 30}


def _compute_impact(run_id: str, grade: str) -> dict:
    """
    Estimate annual energy/cost/CO2 savings for the building from its own
    consumption baseline and a grade-derived optimization potential.
    Reads the per-run building CSV written by the pipeline.
    """
    savings_pct = GRADE_SAVINGS.get(str(grade).upper(), 12)
    impact = {
        "savings_pct": savings_pct,
        "annual_kwh": None, "kwh_saved": None, "cost_saved": None,
        "co2_saved": None, "currency": CURRENCY, "tariff": TARIFF_PER_KWH,
    }
    bpath = os.path.join("data/task_outputs", f"{run_id}_building.csv")
    if os.path.exists(bpath):
        try:
            e = pd.read_csv(bpath, usecols=["electricity_kwh"])["electricity_kwh"].dropna()
            if len(e):
                annual_kwh = float(e.mean() * 8760)  # hourly mean -> annualised
                kwh_saved = annual_kwh * savings_pct / 100.0
                impact.update({
                    "annual_kwh": round(annual_kwh),
                    "kwh_saved": round(kwh_saved),
                    "cost_saved": round(kwh_saved * TARIFF_PER_KWH),
                    "co2_saved": round(kwh_saved * CO2_KG_PER_KWH),
                })
        except Exception as e:
            logger.warning(f"Impact computation failed: {e}")
    return impact


@tool("Generate Forecast Chart")
def generate_forecast_chart(forecast_json: str) -> str:
    """
    Generates a Plotly line chart for the 24-hour utility energy forecast and returns it as a base64 PNG string.
    Input: JSON string containing forecast data with 'timestamp', 'yhat', 'yhat_lower', 'yhat_upper'.
    Output: base64 PNG image string.
    """
    try:
        data = json.loads(forecast_json)
        
        # Handle both array and object formats
        if isinstance(data, dict) and 'forecast' in data:
            data = data['forecast']
        
        df = pd.DataFrame(data)
        if df.empty:
            return ""

        # Rename columns if needed
        if 'ds' in df.columns:
            df.rename(columns={'ds': 'timestamp'}, inplace=True)

        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
        df = df.sort_values(by='timestamp')

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=list(df['timestamp']) + list(df['timestamp'])[::-1],
            y=list(df['yhat_upper']) + list(df['yhat_lower'])[::-1],
            fill='toself',
            fillcolor='rgba(0,0,0,0.08)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name='Confidence Interval'
        ))

        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['yhat'],
            mode='lines',
            name='Forecast',
            line=dict(color='#111111', width=2)
        ))

        now_ts = df['timestamp'].iloc[0]
        fig.add_vline(x=now_ts, line_width=1.5, line_dash="dash", line_color="#c0392b")

        fig.update_layout(
            title="24-Hour Energy Demand Forecast",
            xaxis_title="Time",
            yaxis_title="Energy Demand (kWh)",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Aptos, Segoe UI, sans-serif", color="#333333", size=12),
            colorway=['#111111', '#888888'],
            width=800,
            height=400
        )
        img_bytes = pio.to_image(fig, format='png')
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error generating forecast chart: {e}")
        return ""


@tool("Generate Efficiency Trend Chart")
def generate_efficiency_trend_chart(data_json: str) -> str:
    """
    Generates a Plotly line chart for the iKW-TR efficiency trend and returns it as a base64 PNG string.
    Input: JSON string containing historical data with 'timestamp' and 'iKW_TR'.
    Output: base64 PNG image string.
    """
    try:
        data = json.loads(data_json)
        
        # Simple fallback if data is just efficiency scorecard
        if isinstance(data, dict) and 'avg_ikwtr' in data:
            # Create a simple bar chart instead
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['Current', 'Benchmark', 'Min', 'Max'],
                y=[data.get('avg_ikwtr', 0), 0.60, data.get('min_ikwtr', 0), data.get('max_ikwtr', 0)],
                marker_color=['#111111', '#1b7a3d', '#888888', '#bbbbbb']
            ))
            fig.update_layout(
                title="iKW-TR Efficiency Comparison",
                yaxis_title="iKW-TR",
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Aptos, Segoe UI, sans-serif", color="#333333", size=12),
                width=800,
                height=400
            )
            img_bytes = pio.to_image(fig, format='png')
            return base64.b64encode(img_bytes).decode('utf-8')
        
        df = pd.DataFrame(data)
        if df.empty:
            return ""

        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
        df = df.sort_values(by='timestamp').head(100)  # Limit to 100 points

        colors = []
        for val in df['iKW_TR']:
            if val < 0.65:
                colors.append('#1b7a3d')
            elif val <= 0.80:
                colors.append('#555555')
            else:
                colors.append('#c0392b')

        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['iKW_TR'],
            mode='lines+markers',
            name='iKW-TR',
            line=dict(color='#111111'),
            marker=dict(color=colors, size=8)
        ))

        fig.add_hline(y=0.60, line_dash="dash", line_color="#1b7a3d", annotation_text="Benchmark (0.60)")
        fig.add_hline(y=0.85, line_dash="dash", line_color="#c0392b", annotation_text="Poor (0.85)")

        fig.update_layout(
            title="iKW-TR Efficiency Trend (Benchmark: 0.60 kW/TR)",
            xaxis_title="Time",
            yaxis_title="iKW-TR",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Aptos, Segoe UI, sans-serif", color="#333333", size=12),
            width=800,
            height=400
        )
        
        img_bytes = pio.to_image(fig, format='png')
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error generating efficiency trend chart: {e}")
        return ""


@tool("Generate Energy Heatmap")
def generate_energy_heatmap(data_json: str) -> str:
    """
    Generates a Plotly heatmap for energy consumption by hour and day.
    Input: JSON string containing data with 'hour_of_day', 'day_of_week', and 'meter_reading' / 'electricity_kwh'.
    Output: base64 PNG image string.
    """
    try:
        data = json.loads(data_json)
        
        # Handle forecast format
        if isinstance(data, dict) and 'forecast' in data:
            data = data['forecast']
        
        df = pd.DataFrame(data)
        if df.empty:
            return ""
        
        # Try to derive hour/day from timestamp
        if 'timestamp' in df.columns or 'ds' in df.columns:
            ts_col = 'timestamp' if 'timestamp' in df.columns else 'ds'
            df[ts_col] = pd.to_datetime(df[ts_col], utc=True).dt.tz_localize(None)
            df['hour_of_day'] = df[ts_col].dt.hour
            df['day_of_week'] = df[ts_col].dt.dayofweek
            
        value_col = 'yhat' if 'yhat' in df.columns else 'electricity_kwh'
        if value_col not in df.columns:
            value_col = list(df.select_dtypes(include='number').columns)[0]

        if 'hour_of_day' not in df.columns or 'day_of_week' not in df.columns:
            return ""

        heatmap_data = df.pivot_table(index='day_of_week', columns='hour_of_day', values=value_col, aggfunc='mean')

        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Hour of Day", y="Day of Week", color="Avg Energy (kWh)"),
            x=list(heatmap_data.columns),
            y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            color_continuous_scale='Greys'
        )

        fig.update_layout(
            title="Energy Consumption Heatmap (kWh by Hour and Day)",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Aptos, Segoe UI, sans-serif", color="#333333", size=12),
            width=800,
            height=400
        )
        
        img_bytes = pio.to_image(fig, format='png')
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error generating heatmap: {e}")
        return ""


@tool("Render HTML Report")
def render_html_report(run_id: str, building_id: str = "unknown") -> str:
    """
    Renders HTML report by loading saved task outputs from disk.
    """
    try:
        logger.info(f"📝 Rendering HTML report for {run_id}")
        
        # Load saved task outputs
        output_dir = "data/task_outputs"
        
        def load_json_safe(filename, default=None):
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        logger.info(f"✓ Loaded {filename}: {type(data)} with {len(data) if isinstance(data, (list, dict)) else 0} items")
                        return data
                except Exception as e:
                    logger.warning(f"Could not load {filename}: {e}")
                    return default or {}
            else:
                logger.warning(f"File not found: {filepath}")
                return default or {}
        
        # Load all outputs
        efficiency_raw = load_json_safe(f"{run_id}_efficiency.json", {})
        anomaly_raw = load_json_safe(f"{run_id}_anomalies.json", [])
        forecast_raw = load_json_safe(f"{run_id}_forecast.json", {})
        recommendations_raw = load_json_safe(f"{run_id}_recommendations.json", {})
        maintenance_raw = load_json_safe(f"{run_id}_maintenance.json", {})
        data_quality_raw = load_json_safe(f"{run_id}_data_quality.json", [])
        
        # ===================================================================
        # NORMALIZE DATA STRUCTURES TO MATCH TEMPLATE
        # ===================================================================
        
        # 1. Data Quality Scorecard
        if isinstance(data_quality_raw, list):
            dq_list = data_quality_raw
        elif isinstance(data_quality_raw, dict) and "columns" in data_quality_raw:
            dq_list = data_quality_raw["columns"]
        else:
            dq_list = []
        
        logger.info(f"Data quality items: {len(dq_list)}")
        
        # 2. Efficiency
        if isinstance(efficiency_raw, dict):
            efficiency_formatted = {
                "current_avg_ikwtr": efficiency_raw.get("avg_ikwtr", 0),
                "grade": efficiency_raw.get("efficiency_grade", "N/A"),
                "trend_direction": "down",
                "trend_percentage": 0
            }
        else:
            efficiency_formatted = {
                "current_avg_ikwtr": 0,
                "grade": "N/A",
                "trend_direction": "down",
                "trend_percentage": 0
            }
        
        # 3. Anomaly Report (new format: {"total_anomalies": N, "anomalies": [...]})
        anomaly_list = []
        total_anomalies = None
        if isinstance(anomaly_raw, dict):
            if "anomalies" in anomaly_raw:
                anomaly_list = anomaly_raw["anomalies"] or []
                total_anomalies = anomaly_raw.get("total_anomalies", len(anomaly_list))
            elif "anomaly_count" in anomaly_raw and "anomaly_timestamps" in anomaly_raw:
                total_anomalies = anomaly_raw.get("anomaly_count")
                for ts in anomaly_raw.get("anomaly_timestamps", [])[:10]:
                    anomaly_list.append({
                        "timestamp": ts, "parameter": "Multiple", "severity": "MEDIUM",
                        "root_cause": "Isolation Forest Detection",
                        "description": "Detected via multivariate anomaly detection",
                    })
            elif "timestamp" in anomaly_raw:
                anomaly_list = [anomaly_raw]
        elif isinstance(anomaly_raw, list):
            anomaly_list = anomaly_raw

        if total_anomalies is None:
            total_anomalies = len(anomaly_list)

        # Backfill any missing fields defensively
        for a in anomaly_list:
            a.setdefault("parameter", "Multiple")
            a.setdefault("severity", "MEDIUM")
            a.setdefault("timestamp", "Unknown")
            a.setdefault("root_cause", "Unknown")
            a.setdefault("description", "Anomaly detected")

        logger.info(f"Anomaly items shown: {len(anomaly_list)} of {total_anomalies} total")
        
        # 4. Recommendations
        recs_list = []
        if isinstance(recommendations_raw, dict):
            if "recommendations" in recommendations_raw:
                recs_list = recommendations_raw["recommendations"]
            elif "action" in recommendations_raw:
                recs_list = [recommendations_raw]
        elif isinstance(recommendations_raw, list):
            recs_list = recommendations_raw
        
        # Ensure each recommendation has required fields
        for i, rec in enumerate(recs_list):
            if "rank" not in rec:
                rec["rank"] = i + 1
            if "category" not in rec:
                rec["category"] = "General"
            if "action" not in rec:
                rec["action"] = "No action specified"
            if "rationale" not in rec:
                rec["rationale"] = "No rationale provided"
            if "expected_impact" not in rec:
                rec["expected_impact"] = "Unknown"
            if "priority" not in rec:
                rec["priority"] = "MEDIUM"
        
        logger.info(f"Recommendation items: {len(recs_list)}")
        
        # 5. Maintenance
        maint_list = []
        if isinstance(maintenance_raw, dict):
            # Ensure required fields
            if "priority" not in maintenance_raw and "priority_level" in maintenance_raw:
                maintenance_raw["priority"] = maintenance_raw["priority_level"]
            if "recommended_action" not in maintenance_raw and "recommended_maintenance_action" in maintenance_raw:
                maintenance_raw["recommended_action"] = maintenance_raw["recommended_maintenance_action"]
            if "urgency_days" not in maintenance_raw:
                maintenance_raw["urgency_days"] = 7
            
            maint_list = [maintenance_raw]
        elif isinstance(maintenance_raw, list):
            maint_list = maintenance_raw
        
        logger.info(f"Maintenance items: {len(maint_list)}")
        
        # ===================================================================
        # GENERATE CHARTS
        # ===================================================================
        forecast_chart_b64 = ""
        efficiency_chart_b64 = ""
        heatmap_chart_b64 = ""
        
        # Load the per-building dataset so efficiency trend + heatmap use REAL
        # measured history (not the forecast). Downsample for clean rendering.
        building_csv = os.path.join(output_dir, f"{run_id}_building.csv")
        bdf = None
        if os.path.exists(building_csv):
            try:
                bdf = pd.read_csv(building_csv)
                bdf['timestamp'] = pd.to_datetime(bdf['timestamp'], utc=True, errors='coerce').dt.tz_localize(None)
                bdf = bdf.dropna(subset=['timestamp'])
            except Exception as e:
                logger.warning(f"Could not read building csv for charts: {e}")
                bdf = None

        try:
            if forecast_raw and isinstance(forecast_raw, dict) and forecast_raw.get("forecast"):
                forecast_chart_b64 = generate_forecast_chart.func(json.dumps(forecast_raw))
                logger.info("✓ Forecast chart generated")
        except Exception as e:
            logger.warning(f"Forecast chart failed: {e}")

        try:
            if bdf is not None and 'iKW_TR' in bdf.columns and bdf['iKW_TR'].notna().any():
                daily = (bdf.set_index('timestamp')['iKW_TR'].resample('D').mean().dropna().reset_index())
                series = [{"timestamp": r['timestamp'].strftime("%Y-%m-%dT%H:%M:%SZ"), "iKW_TR": round(float(r['iKW_TR']), 4)} for _, r in daily.iterrows()]
                if series:
                    efficiency_chart_b64 = generate_efficiency_trend_chart.func(json.dumps(series))
            elif isinstance(efficiency_raw, dict) and efficiency_raw.get("avg_ikwtr"):
                efficiency_chart_b64 = generate_efficiency_trend_chart.func(json.dumps(efficiency_raw))
            logger.info("✓ Efficiency chart generated")
        except Exception as e:
            logger.warning(f"Efficiency chart failed: {e}")

        try:
            if bdf is not None and 'electricity_kwh' in bdf.columns:
                hm = bdf[['hour_of_day', 'day_of_week', 'electricity_kwh']].dropna() if 'hour_of_day' in bdf.columns else None
                if hm is None or hm.empty:
                    hm = bdf.assign(hour_of_day=bdf['timestamp'].dt.hour, day_of_week=bdf['timestamp'].dt.dayofweek)[['hour_of_day', 'day_of_week', 'electricity_kwh']].dropna()
                heatmap_chart_b64 = generate_energy_heatmap.func(hm.to_json(orient='records'))
            logger.info("✓ Heatmap generated")
        except Exception as e:
            logger.warning(f"Heatmap failed: {e}")
        
        # ===================================================================
        # PREPARE TEMPLATE DATA
        # ===================================================================
        run_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Real efficiency trend: compare the most recent 30 days vs the prior 30
        if bdf is not None and 'iKW_TR' in bdf.columns and len(bdf) > 100:
            try:
                s = bdf.sort_values('timestamp')
                cutoff = s['timestamp'].max() - pd.Timedelta(days=30)
                recent = s[s['timestamp'] >= cutoff]['iKW_TR'].mean()
                prior = s[s['timestamp'] < cutoff]['iKW_TR'].mean()
                if pd.notnull(recent) and pd.notnull(prior) and prior:
                    pct = (recent - prior) / prior * 100.0
                    efficiency_formatted["trend_direction"] = "up" if pct > 0 else "down"
                    efficiency_formatted["trend_percentage"] = round(abs(pct), 1)
            except Exception:
                pass

        anomaly_phrase = (
            "No statistically significant anomalies were detected"
            if total_anomalies == 0 else
            f"Detected {total_anomalies} genuine anomal{'y' if total_anomalies == 1 else 'ies'} "
            f"(showing the {len(anomaly_list)} most severe)"
        )
        executive_summary = (
            f"HVAC analysis completed for {building_id.replace('_', ' ')}. "
            f"Efficiency grade {efficiency_formatted['grade']}. "
            f"{anomaly_phrase}. "
            f"Generated {len(recs_list)} optimization recommendation{'' if len(recs_list) == 1 else 's'}."
        )

        # Estimated annual energy/cost/CO2 impact for this building
        impact = _compute_impact(run_id, efficiency_formatted.get("grade", "C"))
        
        # ===================================================================
        # RENDER TEMPLATE
        # ===================================================================
        template_dir = os.path.join(os.getcwd(), 'backend', 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('report_template.html')

        html_out = template.render(
            building_id=building_id,
            run_date=run_date,
            executive_summary=executive_summary,
            impact=impact,
            data_quality_scorecard=dq_list,
            efficiency=efficiency_formatted,
            anomaly_report=anomaly_list,
            total_anomalies=total_anomalies,
            forecast_chart_b64=forecast_chart_b64,
            efficiency_chart_b64=efficiency_chart_b64,
            heatmap_chart_b64=heatmap_chart_b64,
            recommendations=recs_list,
            maintenance=maint_list
        )

        output_dir_html = os.path.join(os.getcwd(), 'reports', 'html')
        os.makedirs(output_dir_html, exist_ok=True)
        html_path = os.path.join(output_dir_html, f"{run_id}.html")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_out)

        logger.info(f"✅ HTML report saved to {html_path}")
        logger.info(f"   - Data quality: {len(dq_list)} items")
        logger.info(f"   - Anomalies: {len(anomaly_list)} items")
        logger.info(f"   - Recommendations: {len(recs_list)} items")
        logger.info(f"   - Maintenance: {len(maint_list)} items")
        
        return os.path.abspath(html_path)
        
    except Exception as e:
        error_msg = f"Error rendering HTML: {str(e)}"
        logger.error(f"❌ {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        return error_msg

def _html_to_pdf(html_file, pdf_path) -> str:
    """
    Convert an HTML file to PDF, cross-platform.

    Prefers wkhtmltopdf (pdfkit) when its binary is actually present — typically
    a Windows dev box — and otherwise uses WeasyPrint, which is pure Python and
    needs no external binary (its Pango/Cairo libs ship in the Docker image).
    wkhtmltopdf was removed from Debian 13, so Linux/containers use WeasyPrint.
    Returns the engine name used.
    """
    import shutil

    wk_path = os.getenv("WKHTMLTOPDF_PATH")
    if not wk_path:
        win_default = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        if os.path.exists(win_default):
            wk_path = win_default
        elif shutil.which("wkhtmltopdf"):
            wk_path = shutil.which("wkhtmltopdf")

    # Only use wkhtmltopdf if pdfkit is installed AND the binary really exists.
    if wk_path and PDFKIT_AVAILABLE and os.path.exists(wk_path):
        config = pdfkit.configuration(wkhtmltopdf=wk_path)
        pdfkit.from_file(str(html_file), str(pdf_path), configuration=config)
        return "wkhtmltopdf"

    # Fallback: WeasyPrint (no external binary required).
    from weasyprint import HTML
    HTML(filename=str(html_file)).write_pdf(str(pdf_path))
    return "weasyprint"


@tool("PDF Report Generator")
def generate_pdf_report(html_path: str, run_id: str = None) -> str:
    """
    Converts HTML report to PDF using pdfkit.
    
    Args:
        html_path: Full path to HTML file (NOT a placeholder!)
        run_id: Run identifier
        
    Returns:
        JSON with pdf_path or error
    """
    import time
    from pathlib import Path
    
    try:
        logger.info(f"📄 Generating PDF from: {html_path}")
        
        # Validate input
        if not html_path or html_path == "/path/to/report.html" or "path/to" in html_path:
            error_msg = f"Invalid HTML path: {html_path}. This is a placeholder, not a real path!"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        
        html_file = Path(html_path)
        
        # If file doesn't exist, try to find it
        if not html_file.exists():
            logger.warning(f"HTML file not found at {html_path}, searching...")
            
            possible_paths = [
                Path(html_path),
                Path("reports/html") / f"{run_id}.html",
                Path(os.getcwd()) / "reports" / "html" / f"{run_id}.html",
            ]
            
            html_file = None
            
            # Wait up to 5 seconds for file to appear (in case of race condition)
            for attempt in range(5):
                for candidate in possible_paths:
                    if candidate.exists():
                        html_file = candidate
                        logger.info(f"✓ Found HTML file at: {html_file}")
                        break
                
                if html_file:
                    break
                
                logger.debug(f"Attempt {attempt + 1}/5: File not found, waiting 1s...")
                time.sleep(1)
            
            if html_file is None or not html_file.exists():
                error_msg = f"HTML file not found after 5 attempts. Tried: {[str(p) for p in possible_paths]}"
                logger.error(error_msg)
                return json.dumps({"error": error_msg})
        
        # Ensure HTML file is valid
        if html_file.stat().st_size == 0:
            error_msg = f"HTML file is empty: {html_file}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        
        logger.info(f"✓ HTML file verified: {html_file} ({html_file.stat().st_size} bytes)")
        
        # Create PDF path
        pdf_path = Path("reports/pdf") / (html_file.stem + ".pdf")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {html_file.name} → {pdf_path.name}")

        engine = _html_to_pdf(html_file, pdf_path)
        logger.info(f"PDF rendered with {engine}")

        # Verify PDF was created
        if not pdf_path.exists():
            error_msg = "PDF conversion completed but file not found"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        
        logger.info(f"✅ PDF report saved: {pdf_path} ({pdf_path.stat().st_size} bytes)")
        
        return json.dumps({
            "pdf_path": str(pdf_path),
            "html_path": str(html_file),
            "status": "success"
        })
        
    except Exception as e:
        error_msg = f"PDF generation failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return json.dumps({"error": error_msg})