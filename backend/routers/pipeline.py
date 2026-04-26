"""
Pipeline router.

This module provides endpoints to trigger the HVAC multi-agent pipeline and
to poll run status.
"""

from __future__ import annotations

from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from ..database import PipelineRun, get_db_session


router = APIRouter()


class PipelineRunCreateRequest(BaseModel):
    """
    Request payload for triggering a pipeline run.

    Notes:
    - This is intentionally permissive/stub-friendly; the pipeline execution
      itself is implemented later.
    """

    building_id: str = Field(..., description="Building identifier.")

    dataset_path: str | None = Field(
        None,
        description="Optional path to the uploaded dataset (CSV).",
    )
    weather_path: str | None = Field(
        None,
        description="Optional path to the uploaded weather dataset (CSV).",
    )
    forecast_horizon_hours: int = Field(
        24,
        ge=1,
        le=168,
        description="Forecast horizon in hours.",
    )

    # CHANGED: Matched keys to what Dashboard.jsx is sending
    latitude: float | None = Field(None, description="Latitude for weather adjustments.")
    longitude: float | None = Field(None, description="Longitude for weather adjustments.")


class PipelineRunCreateResponse(BaseModel):
    """Response returned immediately after creating a pipeline run."""

    run_id: str
    status: str


class PipelineRunStatusResponse(BaseModel):
    """Pipeline status payload returned by polling."""

    run_id: str
    building_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    duration_s: float | None = None
    error_msg: str | None = None
    progress: int = 0  # CHANGED: Added to support the React frontend progress bar


class PipelineStatsResponse(BaseModel):
    """Aggregation of pipeline metrics for the dashboard."""
    buildings_analyzed: int
    success_rate: int
    reports_generated: int
    total_runs: int


def _generate_run_id() -> str:
    """
    Generate a unique run identifier.

    Returns:
        A string run id suitable for URL usage.
    """

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"run_{ts}_{suffix}"


@router.post("/api/v1/pipeline/run", response_model=PipelineRunCreateResponse)
async def run_pipeline_endpoint(
    request: PipelineRunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
) -> PipelineRunCreateResponse:
    """
    Trigger a new pipeline run.
    
    This endpoint creates a `PipelineRun` row in the SQLite database, marks
    it as `queued`, and dispatches the execution to a background task.
    """

    try:
        run_id = _generate_run_id()
        run = PipelineRun(
            run_id=run_id,
            building_id=request.building_id,
            status="RUNNING", # Changed from queued to running so UI updates immediately
        )
        db.add(run)
        db.commit()
        
        inputs = request.model_dump()
        inputs["run_id"] = run_id  # ENSURE agents have access to the Run ID
        inputs["metadata_path"] = "data/raw/metadata.csv"
        
        # CHANGED: Map React's 'latitude'/'longitude' back to 'lat'/'lon' for CrewAI
        inputs["lat"] = inputs.pop("latitude", 40.7128) or 40.7128
        inputs["lon"] = inputs.pop("longitude", -74.0060) or -74.0060
        
        # CHANGED: Provide the missing data Agent 4 is begging for
        inputs["load_pct"] = 75.0
        inputs["num_chillers"] = 3
        inputs["peak_windows_json"] = '{"peak_start": "14:00", "peak_end": "18:00"}'
        
        from ..pipeline import run_pipeline
        background_tasks.add_task(run_pipeline, run_id, inputs)
        
        return PipelineRunCreateResponse(run_id=run_id, status="RUNNING")
    except Exception as exc:  # noqa: BLE001 - boundary for API error handling
        logger.exception("Failed to create pipeline run: {}", exc)
        raise HTTPException(status_code=500, detail="Failed to start pipeline run.") from exc


@router.get(
    "/api/v1/pipeline/status/{run_id}",
    response_model=PipelineRunStatusResponse,
)
async def get_pipeline_status(
    run_id: str,
    db: Session = Depends(get_db_session),
) -> PipelineRunStatusResponse:
    """
    Poll the status of a pipeline run by `run_id`.
    """

    try:
        run: PipelineRun | None = db.get(PipelineRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found.")

        from ..pipeline import run_progress
        
        current_progress = 0
        status_upper = run.status.upper()
        if status_upper == "COMPLETED":
            current_progress = 100
        elif status_upper == "FAILED":
            current_progress = run_progress.get(run_id, 0)
        elif status_upper == "RUNNING":
            current_progress = run_progress.get(run_id, 10)

        return PipelineRunStatusResponse(
            run_id=run.run_id,
            building_id=run.building_id,
            status=status_upper,
            created_at=run.created_at,
            completed_at=run.completed_at,
            duration_s=run.duration_s,
            error_msg=run.error_msg,
            progress=current_progress
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary for API error handling
        logger.exception("Failed to get pipeline status for {}: {}", run_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline status.") from exc


@router.get("/api/v1/pipeline/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats(db: Session = Depends(get_db_session)) -> PipelineStatsResponse:
    """
    Fetch aggregated stats for the dashboard stat cards.
    """
    try:
        from sqlalchemy import func, distinct, select

        # Unique buildings
        buildings_stmt = select(func.count(distinct(PipelineRun.building_id)))
        buildings_count = db.execute(buildings_stmt).scalar() or 0

        # Success rate and reports
        total_stmt = select(func.count(PipelineRun.run_id))
        total_count = db.execute(total_stmt).scalar() or 0

        success_stmt = select(func.count(PipelineRun.run_id)).where(PipelineRun.status == "completed")
        success_count = db.execute(success_stmt).scalar() or 0

        success_rate = 0
        if total_count > 0:
            success_rate = int((success_count / total_count) * 100)

        return PipelineStatsResponse(
            buildings_analyzed=buildings_count,
            success_rate=success_rate,
            reports_generated=success_count,
            total_runs=total_count
        )
    except Exception as exc:
        logger.exception("Failed to fetch dashboard stats: {}", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch stats.") from exc