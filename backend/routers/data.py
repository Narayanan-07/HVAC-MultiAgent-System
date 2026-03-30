"""
Data router.

This module accepts CSV uploads and stores them under `data/raw/`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File
import pandas as pd
from loguru import logger

from ..config import settings


router = APIRouter()

_RAW_DIR: Final[Path] = Path(settings.DATA_DIR) / "raw"


@router.post("/api/v1/data/upload")
async def upload_csv(
    file: UploadFile = File(..., description="The CSV file to upload."),
    filename: str | None = Query(
        default=None,
        description="Optional output filename (e.g., dataset.csv).",
    ),
) -> dict:
    """
    Upload a CSV dataset and persist it to `data/raw/`.
    Validates file is a CSV and counts rows/columns.
    """
    try:
        body = await file.read()
        if not body:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        _RAW_DIR.mkdir(parents=True, exist_ok=True)

        chosen_name = filename or file.filename or f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Basic sanitation: keep only the last path segment.
        chosen_name = Path(chosen_name).name
        if not chosen_name.lower().endswith(".csv"):
            chosen_name += ".csv"

        save_path = _RAW_DIR / chosen_name
        save_path.write_bytes(body)

        # Validate with pandas
        try:
            df = pd.read_csv(save_path)
            rows, columns = df.shape
            validation_status = "success"
        except Exception as e:
            # If it fails to parse, it might not be a valid CSV
            save_path.unlink(missing_ok=True)
            logger.exception("Invalid CSV file uploaded: {}", e)
            raise HTTPException(status_code=400, detail="Invalid CSV file format.") from e

        return {
            "filename": chosen_name,
            "rows": rows,
            "columns": columns,
            "validation_status": validation_status,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary for API error handling
        logger.exception("CSV upload failed: {}", exc)
        raise HTTPException(status_code=500, detail="Failed to upload CSV file.") from exc

