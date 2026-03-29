"""
Standalone data preparation orchestrator for Phase 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from backend.agents.tools.data_tools import (
    derive_humidity_wbt_ikwtr,
    engineer_features,
    generate_quality_report,
    handle_missing_values,
    load_and_prepare_data,
)


def run_data_preparation(base_path: str) -> dict[str, Any]:
    """
    Execute the full data preparation flow and return a quality report.

    Sequence:
        1) load_and_prepare_data
        2) handle_missing_values
        3) derive_humidity_wbt_ikwtr
        4) engineer_features
        5) generate_quality_report

    Args:
        base_path: Raw data base path (e.g., `data/raw`).

    Returns:
        Quality report dictionary.
    """

    try:
        logger.info("Starting data preparation pipeline with base path: {}", base_path)

        df = load_and_prepare_data(base_path)
        df = handle_missing_values(df)
        df = derive_humidity_wbt_ikwtr(df)
        df = engineer_features(df)
        quality_report = generate_quality_report(df)

        out_dir = Path("data/processed")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "features_final.csv"
        df.to_csv(out_file, index=False)

        logger.info("Saved final feature dataset to {}", out_file.as_posix())
        logger.info(
            "Data preparation complete. Quality score: {}, flag: {}",
            quality_report["quality_score"],
            quality_report["quality_flag"],
        )
        return quality_report
    except Exception as exc:
        logger.exception("run_data_preparation failed: {}", exc)
        raise RuntimeError(f"Data preparation pipeline failed: {exc}") from exc

