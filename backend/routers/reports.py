"""
Reports router.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from ..database import get_db_session, PipelineRun
from ..config import settings


router = APIRouter()

class PipelineRunResponse(BaseModel):
    run_id: str
    building_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    duration_s: float | None = None
    error_msg: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    run_id: str
    status: str
    pdf_path: str | None = None
    html_path: str | None = None
    html_content: str | None = None
    error_msg: str | None = None


@router.get("/api/v1/reports/{run_id}", response_model=ReportResponse)
async def get_report(run_id: str, db: Session = Depends(get_db_session)) -> ReportResponse:
    """
    Retrieve report details, reading HTML directly if available,
    otherwise returning status from DB.
    """
    stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
    run = db.execute(stmt).scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")

    pdf_file = Path("reports/pdf") / f"{run_id}.pdf"
    html_file = Path("reports/html") / f"{run_id}.html"

    pdf_path = str(pdf_file) if pdf_file.exists() else None
    html_path = str(html_file) if html_file.exists() else None
    
    html_content = None
    if html_file.exists():
        try:
            html_content = html_file.read_text(encoding="utf-8")
        except Exception:
            pass

    return ReportResponse(
        run_id=run.run_id,
        status=run.status,
        pdf_path=pdf_path,
        html_path=html_path,
        html_content=html_content,
        error_msg=run.error_msg
    )


@router.get("/api/v1/reports/{run_id}/pdf")
async def get_report_pdf(run_id: str):
    """
    Stream the PDF file directly.
    """
    pdf_file = Path("reports/pdf") / f"{run_id}.pdf"
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="PDF report not found")
        
    return FileResponse(
        path=pdf_file,
        filename=f"{run_id}.pdf",
        media_type="application/pdf"
    )


@router.get("/api/v1/history", response_model=list[PipelineRunResponse])
async def get_history(db: Session = Depends(get_db_session)) -> list[PipelineRunResponse]:
    """
    List last 20 pipeline runs.
    """
    stmt = select(PipelineRun).order_by(desc(PipelineRun.created_at)).limit(20)
    runs = db.execute(stmt).scalars().all()
    return list(runs)

