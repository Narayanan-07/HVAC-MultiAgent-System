"""
Reports router.

This module currently exposes a stub endpoint to retrieve report artifacts
associated with a `run_id`.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class ReportsResponseStub(BaseModel):
    """
    Stubbed response for report retrieval.

    In the full implementation, these fields will be populated after the
    pipeline completes and report files are generated.
    """

    run_id: str
    status: str = "not_implemented"
    pdf_path: str | None = None
    html_path: str | None = None
    html_content: str | None = None


@router.get("/api/v1/reports/{run_id}", response_model=ReportsResponseStub)
async def get_report(run_id: str) -> ReportsResponseStub:
    """
    Retrieve a generated report for a pipeline run (stub).
    """

    return ReportsResponseStub(run_id=run_id)

