"""
FastAPI application entrypoint.

This app provides the REST API layer for triggering and monitoring the
multi-agent HVAC optimization pipeline.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import settings
from backend.database import create_all
from backend.routers.data import router as data_router
from backend.routers.pipeline import router as pipeline_router
from backend.routers.reports import router as reports_router


class _InterceptHandler(logging.Handler):
    """Route stdlib logging records through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    """Configure Loguru as the sole logging backend, intercepting stdlib logging."""

    logger.remove()
    logger.add(sys.stdout, level=settings.LOG_LEVEL)

    Path("logs").mkdir(exist_ok=True)
    logger.add(
        "logs/hvac_{time:YYYY-MM-DD}.log",
        rotation="50 MB",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8",
    )

    # Route all stdlib logging (used by llm.py, crew.py, litellm, etc.) through Loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging.getLogger(name).handlers = [_InterceptHandler()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan hook — creates DB tables and validates API keys on startup."""

    logger.info("Starting service - creating DB tables (if missing).")
    create_all()

    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        logger.warning(
            "Neither GROQ_API_KEY nor GEMINI_API_KEY is set. "
            "Pipeline runs will fail. Set at least one key in your .env file."
        )
    elif not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — pipeline will use Gemini as primary LLM.")
    elif not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — no LLM fallback available if Groq rate-limits.")

    yield
    logger.info("Service shutdown complete.")


configure_logging()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "app://.",
        "file://",
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

