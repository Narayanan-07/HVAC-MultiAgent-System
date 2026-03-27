"""
FastAPI application entrypoint.

This app provides the REST API layer for triggering and monitoring the
multi-agent HVAC optimization pipeline.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import settings
from backend.database import create_all
from backend.routers.data import router as data_router
from backend.routers.pipeline import router as pipeline_router
from backend.routers.reports import router as reports_router


def configure_logging() -> None:
    """
    Configure Loguru as the sole logging backend for this service.
    """

    logger.remove()
    logger.add(sys.stdout, level=settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan hook.

    Creates database tables on startup.
    """

    logger.info("Starting service - creating DB tables (if missing).")
    create_all()
    yield
    logger.info("Service shutdown complete.")


configure_logging()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)
app.include_router(reports_router)
app.include_router(data_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint.
    """

    return {"status": "ok", "version": "1.0.0"}

