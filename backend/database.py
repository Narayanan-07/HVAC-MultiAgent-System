"""
Database configuration and ORM models.

This module provides:
- SQLAlchemy engine/session setup for SQLite (dev)
- The `PipelineRun` table for tracking pipeline state
- `create_all()` which can be called during FastAPI startup
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import DateTime, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy ORM."""


class PipelineRun(Base):
    """
    Tracks lifecycle and outcome of a pipeline execution.

    Attributes:
        run_id: Unique identifier for the pipeline run.
        building_id: Building identifier tied to the run.
        status: queued | running | completed | failed (string-based for flexibility)
        created_at: UTC creation timestamp.
        completed_at: UTC completion timestamp (nullable while running).
        duration_s: Total duration seconds (nullable while running).
        error_msg: Error message for failed runs (nullable).
    """

    __tablename__ = "pipeline_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_s: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    error_msg: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )


_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # Required for SQLite usage from FastAPI threads.
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_all() -> None:
    """
    Create all database tables.

    Call this during FastAPI startup using the application's lifespan.
    """

    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator:
    """
    FastAPI dependency helper yielding a SQLAlchemy session.

    Yields:
        A SQLAlchemy session instance.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

