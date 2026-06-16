import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from loguru import logger

from backend.database import SessionLocal, PipelineRun
from backend.agents.crew import build_hvac_crew

# Global state to track live progress percentage per run_id
run_progress: dict[str, int] = {}

# Default coordinates (NYC) used only when a building has no stored lat/lng
# and the user supplied none.
_DEFAULT_LAT, _DEFAULT_LON = 40.7128, -74.0060


def _prepare_building_csv(run_id: str, building_id: str) -> tuple[str, float | None, float | None, int]:
    """
    Slice the master processed dataset down to a single building and write a
    per-run CSV the agents will analyze. This is what makes each report
    building-specific — without it, every run analyses all 307 buildings at once.

    Returns: (csv_path, lat, lng, row_count). Reads in chunks to stay memory-safe.
    """
    import pandas as pd
    from pathlib import Path

    src = "data/processed/features_final.csv"
    out_dir = Path("data/task_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}_building.csv"

    frames = []
    for chunk in pd.read_csv(src, chunksize=250_000):
        match = chunk[chunk["building_id"].astype(str) == str(building_id)]
        if len(match):
            frames.append(match)

    df = pd.concat(frames) if frames else pd.DataFrame(columns=pd.read_csv(src, nrows=0).columns)
    df.to_csv(out_path, index=False)

    lat = lng = None
    load_pct = None
    if len(df):
        if "lat" in df.columns and df["lat"].notna().any():
            lat = float(df["lat"].dropna().iloc[0])
        if "lng" in df.columns and df["lng"].notna().any():
            lng = float(df["lng"].dropna().iloc[0])
        # Building-specific load factor for chiller sequencing: recent average
        # demand as a percentage of the building's observed peak.
        if "electricity_kwh" in df.columns and df["electricity_kwh"].notna().any():
            e = df["electricity_kwh"].dropna()
            peak = float(e.quantile(0.99)) or float(e.max())
            recent = float(e.tail(168).mean()) if len(e) >= 168 else float(e.mean())
            if peak > 0:
                load_pct = round(min(100.0, max(5.0, recent / peak * 100.0)), 1)

    logger.info(f"[data] Prepared {len(df)} rows for building '{building_id}' → {out_path}")
    return str(out_path), lat, lng, len(df), load_pct


def _ensure_analysis(run_id: str, data_path: str, inputs: dict) -> None:
    """
    Deterministically compute any analysis outputs the agents did not produce
    (for example when the LLM hit a Groq rate limit mid-run). Runs the SAME
    @tool functions directly on the per-building CSV, so a complete, legitimate
    report is always produced regardless of LLM availability. Never raises.
    """
    import os
    import json

    out = "data/task_outputs"

    def have(name: str) -> bool:
        p = os.path.join(out, f"{run_id}_{name}.json")
        return os.path.exists(p) and os.path.getsize(p) > 2

    def read(name: str, default):
        p = os.path.join(out, f"{run_id}_{name}.json")
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return default

    try:
        import pandas as pd
        from backend.agents.tools.anomaly_tools import (
            generate_data_quality_report, classify_root_cause,
            generate_efficiency_scorecard, score_degradation_trend,
        )
        from backend.agents.tools.forecast_tools import select_best_forecast_model
        from backend.agents.tools.optimization_tools import (
            optimize_setpoints, recommend_chiller_sequencing,
            plan_load_shifting, score_maintenance_priority,
            compile_final_recommendations,
        )

        if not have("data_quality"):
            generate_data_quality_report.func(data_path, run_id)
        if not have("anomalies"):
            classify_root_cause.func(data_path, run_id)
        if not have("efficiency"):
            generate_efficiency_scorecard.func(data_path, run_id)
        if not have("forecast"):
            horizon = int(inputs.get("forecast_horizon_hours", 24) or 24)
            select_best_forecast_model.func(data_path, horizon, run_id)

        deg = json.loads(score_degradation_trend.func(data_path))
        degradation_score = float(deg.get("degradation_score", 0) or 0)

        eff = read("efficiency", {})
        anom = read("anomalies", {})
        total_anom = anom.get("total_anomalies", 0) if isinstance(anom, dict) else 0

        if not have("maintenance"):
            anomaly_report_json = json.dumps({
                "anomaly_count": total_anom,
                "pct_time_above_benchmark": eff.get("pct_time_above_benchmark", 0),
            })
            score_maintenance_priority.func(anomaly_report_json, degradation_score, run_id)

        if not have("recommendations"):
            ambient = 30.0
            try:
                ambient = float(pd.read_csv(data_path, usecols=["airTemperature"])["airTemperature"].dropna().mean())
            except Exception:
                pass
            setpoints = optimize_setpoints.func(json.dumps(eff), ambient)
            sequencing = recommend_chiller_sequencing.func(
                float(inputs.get("load_pct", 75.0) or 75.0),
                int(inputs.get("num_chillers", 3) or 3),
            )
            loadshift = plan_load_shifting.func('[{"peak_start": "14:00", "peak_end": "18:00"}]')
            maint = read("maintenance", {})
            compile_final_recommendations.func(setpoints, sequencing, loadshift, json.dumps(maint), run_id)

        logger.info(f"[analysis] Deterministic safety net complete for {run_id}")
    except Exception as e:  # noqa: BLE001 - fallback must never break the run
        logger.exception(f"[analysis] Deterministic analysis fallback failed for {run_id}: {e}")


def _ensure_report(run_id: str, building_id: str) -> None:
    """
    Deterministically render the HTML + PDF report from the on-disk task
    outputs. Idempotent and safe to call even if the reporter agent already
    produced the files. Never raises — logs and returns on failure so it
    cannot fail an otherwise-successful pipeline run.
    """
    from pathlib import Path
    from backend.agents.tools.report_tools import render_html_report, generate_pdf_report

    try:
        html_file = Path("reports/html") / f"{run_id}.html"
        if not html_file.exists() or html_file.stat().st_size == 0:
            logger.info(f"[report] Rendering HTML for {run_id} (building={building_id})")
            html_path = render_html_report.func(run_id=run_id, building_id=building_id)
        else:
            html_path = str(html_file.resolve())
            logger.info(f"[report] HTML already present for {run_id}")

        pdf_file = Path("reports/pdf") / f"{run_id}.pdf"
        if not pdf_file.exists() or pdf_file.stat().st_size == 0:
            logger.info(f"[report] Generating PDF for {run_id}")
            generate_pdf_report.func(html_path=html_path, run_id=run_id)
        else:
            logger.info(f"[report] PDF already present for {run_id}")
    except Exception as e:  # noqa: BLE001 - report generation must never break the run
        logger.exception(f"[report] Deterministic report generation failed for {run_id}: {e}")

async def run_pipeline(run_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the HVAC multi-agent pipeline.
    """
    logger.info(f"Starting pipeline execution for run_id: {run_id}")
    start_time = time.time()
    
    # Initialize UI progress bar to 10% when starting
    run_progress[run_id] = 10

    db = SessionLocal()
    try:
        run = db.get(PipelineRun, run_id)
        if run:
            run.status = "RUNNING"
            db.commit()
        else:
            logger.warning(f"run_id {run_id} not found in DB at start")
            
        def task_callback(task_output):
            """Called roughly when each agent finishes its task."""
            if run_id in run_progress:
                run_progress[run_id] = min(run_progress[run_id] + 18, 90)
                logger.info(f"Pipeline {run_id} progress advanced to {run_progress[run_id]}%")

        # ------------------------------------------------------------------
        # Slice the dataset to the selected building BEFORE the agents run, so
        # every tool analyses only this building's data. Also resolve the
        # coordinates used for the weather forecast: user-supplied value wins,
        # else the building's own stored lat/lng, else a sensible default.
        # ------------------------------------------------------------------
        building_id = inputs.get("building_id", "unknown")
        data_path, blat, blng, n_rows, bload = await asyncio.to_thread(
            _prepare_building_csv, run_id, building_id
        )
        if n_rows == 0:
            raise ValueError(
                f"No data found for building '{building_id}' in features_final.csv"
            )
        inputs["data_path"] = data_path
        inputs["lat"] = inputs.get("lat") or blat or _DEFAULT_LAT
        inputs["lon"] = inputs.get("lon") or blng or _DEFAULT_LON
        if bload is not None:
            inputs["load_pct"] = bload  # building-specific, overrides router default
        logger.info(
            f"[pipeline] {run_id} building={building_id} rows={n_rows} "
            f"coords=({inputs['lat']:.4f},{inputs['lon']:.4f})"
        )

        crew = build_hvac_crew(task_callback=task_callback)

        # Run the multi-agent pipeline. If the LLM fails (e.g. Groq rate limit),
        # we DON'T abort — the actual analysis does not need the LLM, so we fall
        # through to the deterministic safety net below and still finish the run.
        result = None
        try:
            result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
        except Exception as agent_err:  # noqa: BLE001
            logger.warning(
                f"[pipeline] Agent run errored for {run_id} ({agent_err}); "
                f"continuing with deterministic analysis fallback."
            )

        # ------------------------------------------------------------------
        # SAFETY NET (deterministic, not LLM-dependent):
        #   1. Fill any analysis outputs the agents didn't produce.
        #   2. Render HTML + PDF from the on-disk outputs.
        # Together these guarantee a complete, building-specific report even if
        # the agents partially or fully failed on rate limits.
        # ------------------------------------------------------------------
        await asyncio.to_thread(_ensure_analysis, run_id, data_path, inputs)
        await asyncio.to_thread(_ensure_report, run_id, building_id)

        result_dict = {"raw_output": str(result) if result is not None else "deterministic", "tasks_output": {}}
        if result is not None and hasattr(result, "tasks_output"):
            for t in result.tasks_output:
                result_dict["tasks_output"][t.description] = t.raw

        from pathlib import Path as _Path
        report_ok = (_Path("reports/html") / f"{run_id}.html").exists()
        duration_s = time.time() - start_time

        if run:
            if report_ok:
                run.status = "COMPLETED"
                if result is None:
                    run.error_msg = "Completed via deterministic fallback (LLM unavailable)"
            else:
                run.status = "FAILED"
                run.error_msg = "Report could not be generated"
            run.completed_at = datetime.now(timezone.utc)
            run.duration_s = duration_s
            db.commit()

        run_progress.pop(run_id, None)
        logger.info(f"Pipeline {run_id} finished in {duration_s:.2f}s (report_ok={report_ok})")
        return result_dict

    except Exception as e:
        duration_s = time.time() - start_time
        logger.exception(f"Pipeline execution failed for {run_id}: {e}")

        if db.is_active:
            run = db.get(PipelineRun, run_id)
            if run:
                run.status = "FAILED"
                run.completed_at = datetime.now(timezone.utc)
                run.error_msg = str(e)
                run.duration_s = duration_s
                db.commit()

        run_progress.pop(run_id, None)
                
        raise
    finally:
        db.close()
