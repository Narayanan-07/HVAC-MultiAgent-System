"""
Pipeline router.

This module provides endpoints to trigger the HVAC multi-agent pipeline and
to poll run status.
"""

from __future__ import annotations

from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException
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

    lat: float | None = Field(None, description="Latitude for weather adjustments.")
    lon: float | None = Field(None, description="Longitude for weather adjustments.")


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
async def run_pipeline(
    request: PipelineRunCreateRequest,
    db: Session = Depends(get_db_session),
) -> PipelineRunCreateResponse:
    """
    Trigger a new pipeline run (stub).

    This endpoint creates a `PipelineRun` row in the SQLite database and marks
    it as `queued`. The actual CrewAI execution is added in a later phase.
    """

    try:
        run_id = _generate_run_id()
        run = PipelineRun(
            run_id=run_id,
            building_id=request.building_id,
            status="queued",
        )
        db.add(run)
        db.commit()
        return PipelineRunCreateResponse(run_id=run_id, status="queued")
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

        return PipelineRunStatusResponse(
            run_id=run.run_id,
            building_id=run.building_id,
            status=run.status,
            created_at=run.created_at,
            completed_at=run.completed_at,
            duration_s=run.duration_s,
            error_msg=run.error_msg,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary for API error handling
        logger.exception("Failed to get pipeline status for {}: {}", run_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline status.") from exc

