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

@tool("Generate Forecast Chart")
def generate_forecast_chart(forecast_json: str) -> str:
    """
    Generates a Plotly line chart for the 24-hour utility energy forecast and returns it as a base64 PNG string.
    Input: JSON string containing forecast data with 'timestamp', 'yhat', 'yhat_lower', 'yhat_upper'.
    Output: base64 PNG image string.
    """
    try:
        data = json.loads(forecast_json)
        df = pd.DataFrame(data)
        if df.empty:
            return ""

        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by='timestamp')

        fig = go.Figure()

        # Add shaded area for confidence interval
        fig.add_trace(go.Scatter(
            x=list(df['timestamp']) + list(df['timestamp'])[::-1],
            y=list(df['yhat_upper']) + list(df['yhat_lower'])[::-1],
            fill='toself',
            fillcolor='rgba(0,100,80,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name='95% Confidence Interval'
        ))

        # Add forecast line
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['yhat'],
            mode='lines',
            name='Forecast',
            line=dict(color='blue')
        ))

        # Add vertical line at "now"
        now_ts = df['timestamp'].iloc[0] # Using first point as proxy for "now"
        fig.add_vline(x=now_ts, line_width=2, line_dash="dash", line_color="red")

        fig.update_layout(
            title="24-Hour Energy Demand Forecast with 95% Confidence Interval",
            xaxis_title="Time",
            yaxis_title="Energy Demand (kWh)",
            plot_bgcolor='white',
            width=800,
            height=400
        )
        img_bytes = pio.to_image(fig, format='png')
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        return f"Error generating forecast chart: {str(e)}"


@tool("Generate Efficiency Trend Chart")
def generate_efficiency_trend_chart(data_json: str) -> str:
    """
    Generates a Plotly line chart for the iKW-TR efficiency trend and returns it as a base64 PNG string.
    Input: JSON string containing historical data with 'timestamp' and 'iKW_TR'.
    Output: base64 PNG image string.
    """
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)
        if df.empty:
            return ""

        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by='timestamp')

        colors = []
        for val in df['iKW_TR']:
            if val < 0.65:
                colors.append('green')
            elif val <= 0.80:
                colors.append('yellow')
            else:
                colors.append('red')

        fig = go.Figure()
        
        # Adding a single continuous line, colored markers for thresholds
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['iKW_TR'],
            mode='lines+markers',
            name='iKW-TR',
            line=dict(color='gray'),
            marker=dict(color=colors, size=8)
        ))

        # Add benchmark lines
        fig.add_hline(y=0.60, line_dash="dash", line_color="green", annotation_text="Benchmark (0.60)")
        fig.add_hline(y=0.85, line_dash="dash", line_color="red", annotation_text="Poor (0.85)")

        fig.update_layout(
            title="iKW-TR Efficiency Trend (Benchmark: 0.60 kW/TR)",
            xaxis_title="Time",
            yaxis_title="iKW-TR",
            plot_bgcolor='white',
            width=800,
            height=400
        )
        
        img_bytes = pio.to_image(fig, format='png')
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        return f"Error generating efficiency trend chart: {str(e)}"


@tool("Generate Energy Heatmap")
def generate_energy_heatmap(data_json: str) -> str:
    """
    Generates a Plotly heatmap for energy consumption by hour and day.
    Input: JSON string containing data with 'hour_of_day', 'day_of_week', and 'meter_reading' / 'electricity_kwh'.
    Output: base64 PNG image string.
    """
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)
        if df.empty:
            return ""
            
        value_col = 'meter_reading' if 'meter_reading' in df.columns else 'electricity_kwh'
        if value_col not in df.columns:
            # Fallback if specific column isn't found
            value_col = list(df.select_dtypes(include='number').columns)[0]

        heatmap_data = df.pivot_table(index='day_of_week', columns='hour_of_day', values=value_col, aggfunc='mean')

        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Hour of Day", y="Day of Week", color="Avg Energy (kWh)"),
            x=list(heatmap_data.columns),
            y=list(heatmap_data.index)
        )
        
        fig.update_layout(
            title="Energy Consumption Heatmap (kWh by Hour and Day)",
            width=800,
            height=400
        )
        
        img_bytes = pio.to_image(fig, format='png')
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        return f"Error generating heatmap: {str(e)}"


@tool("Render HTML Report")
def render_html_report(
    data_quality_json: str, 
    efficiency_scorecard_json: str,
    anomaly_report_json: str, 
    forecast_json: str,
    recommendations_json: str, 
    maintenance_json: str,
    building_id: str, 
    run_id: str
) -> str:
    """
    Renders the HTML report using Jinja2 and base64 encoded charts.
    """
    try:
        # Load template
        template_dir = os.path.join(os.getcwd(), 'backend', 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('report_template.html')

        # Parse JSON data
        dq_data = json.loads(data_quality_json)
        eff_scorecard = json.loads(efficiency_scorecard_json)
        anomalies = json.loads(anomaly_report_json)
        recs = json.loads(recommendations_json)
        maintenance = json.loads(maintenance_json)

        # Generate charts - use .func() since it has arguments and is wrapped by @tool
        forecast_chart_b64 = generate_forecast_chart.func(forecast_json)
        efficiency_chart_b64 = generate_efficiency_trend_chart.func(efficiency_scorecard_json)
        heatmap_chart_b64 = generate_energy_heatmap.func(forecast_json)

        run_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        executive_summary = f"Automated HVAC Analysis Report for Building {building_id} completed successfully. Identified {len(anomalies)} anomalies and generated {len(recs)} top recommendations to improve efficiency."

        # Map to template variables
        html_out = template.render(
            building_id=building_id,
            run_date=run_date,
            executive_summary=executive_summary,
            data_quality_scorecard=dq_data,
            efficiency=eff_scorecard,
            anomaly_report=anomalies,
            forecast_chart_b64=forecast_chart_b64,
            efficiency_chart_b64=efficiency_chart_b64,
            heatmap_chart_b64=heatmap_chart_b64,
            recommendations=recs,
            maintenance=maintenance
        )

        output_dir = os.path.join(os.getcwd(), 'reports', 'html')
        os.makedirs(output_dir, exist_ok=True)
        html_path = os.path.join(output_dir, f"{run_id}.html")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_out)

        return html_path
    except Exception as e:
        return f"Error rendering HTML: {str(e)}"


@tool("PDF Report Generator")
def generate_pdf_report(html_path: str) -> str:
    """
    Converts HTML report to PDF using pdfkit.
    Input: html_path (str)
    Output: pdf_path (str)
    """
    try:
        from pathlib import Path
        html_path = Path(html_path)
        pdf_path = Path("reports/pdf") / (html_path.stem + ".pdf")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        config = pdfkit.configuration(
            wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        )
        pdfkit.from_file(str(html_path), str(pdf_path), configuration=config)
        logger.info(f"PDF report saved to {pdf_path}")
        return str(pdf_path)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return json.dumps({"error": str(e)})