"""
Data router.

This module accepts CSV uploads and stores them under `data/raw/`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from fastapi import APIRouter, HTTPException, Request, Query
from loguru import logger

from ..config import settings


router = APIRouter()

_RAW_DIR: Final[Path] = Path(settings.DATA_DIR) / "raw"


@router.post("/api/v1/data/upload")
async def upload_csv(
    request: Request,
    filename: str | None = Query(
        default=None,
        description="Optional output filename (e.g., dataset.csv).",
    ),
) -> dict:
    """
    Upload a CSV dataset and persist it to `data/raw/`.

    Implementation notes:
    - To keep dependencies minimal, this endpoint accepts raw CSV bytes
      in the request body (e.g., `Content-Type: text/csv`).
    - For `multipart/form-data` upload support, `python-multipart` should be
      added later and the endpoint adjusted accordingly.
    """

    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Request body is empty.")

        content_type = (request.headers.get("content-type") or "").lower()
        if ("csv" not in content_type) and filename is None:
            # If the user didn't explicitly provide a filename, require CSV-ish content-type.
            raise HTTPException(
                status_code=400,
                detail="Provide a CSV request body or specify `?filename=...`.",
            )

        _RAW_DIR.mkdir(parents=True, exist_ok=True)

        inferred_ext = ".csv" if (filename is None or not filename.lower().endswith(".csv")) else ""
        chosen_name = filename or f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        if not chosen_name.lower().endswith(".csv"):
            chosen_name = f"{chosen_name}{inferred_ext or '.csv'}"

        # Basic sanitation: keep only the last path segment.
        chosen_name = Path(chosen_name).name

        save_path = _RAW_DIR / chosen_name
        save_path.write_bytes(body)

        return {
            "filename": chosen_name,
            "saved_path": str(save_path),
            "size_bytes": len(body),
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary for API error handling
        logger.exception("CSV upload failed: {}", exc)
        raise HTTPException(status_code=500, detail="Failed to upload CSV file.") from exc

