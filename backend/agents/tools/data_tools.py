"""
Data preparation utilities for HVAC multi-agent pipeline.

This module intentionally defines standalone functions (not CrewAI tools yet)
so they can be unit-tested and composed before agent wrapping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
import numpy as np
import pandas as pd


TARGET_SPACE_USAGE = {"lodging", "office", "retail"}


def _resolve_input_path(base_path: Path, primary_rel_path: str, fallback_name: str) -> Path:
    """
    Resolve a CSV file path with a preferred location and a flat-file fallback.

    Args:
        base_path: Base input directory.
        primary_rel_path: Relative path expected by project structure.
        fallback_name: Fallback CSV filename directly under `base_path`.

    Returns:
        Resolved file path.

    Raises:
        FileNotFoundError: If neither primary nor fallback path exists.
    """

    primary = base_path / primary_rel_path
    fallback = base_path / fallback_name
    if primary.exists():
        return primary
    if fallback.exists():
        logger.warning(
            "Using fallback input path `{}` (primary `{}` not found).",
            fallback,
            primary,
        )
        return fallback
    raise FileNotFoundError(
        f"Missing required file. Checked '{primary}' and fallback '{fallback}'."
    )


def load_and_prepare_data(base_path: str) -> pd.DataFrame:
    """
    Load metadata, meter, and weather CSVs and build the merged raw dataset.

    Steps implemented:
    - metadata filtering for target `primaryspaceusage`
    - chilledwater/electricity melt from wide to long
    - outer merge on timestamp + building_id
    - site_id and building_type extraction
    - weather join on timestamp + site_id
    - drop rows where both energy columns are missing
    - save `data/processed/merged_raw.csv`

    Args:
        base_path: Root path of raw data input.

    Returns:
        Merged dataframe.
    """

    try:
        base = Path(base_path)
        logger.info("Loading raw data from base path: {}", base.resolve())

        metadata_path = _resolve_input_path(base, "metadata/metadata.csv", "metadata.csv")
        chilled_path = _resolve_input_path(base, "meters/raw/chilledwater.csv", "chilledwater.csv")
        electricity_path = _resolve_input_path(base, "meters/raw/electricity.csv", "electricity.csv")
        weather_path = _resolve_input_path(base, "weather/weather.csv", "weather.csv")

        metadata_df = pd.read_csv(metadata_path)
        filtered_meta = metadata_df[
            metadata_df["primaryspaceusage"].astype(str).str.lower().isin(TARGET_SPACE_USAGE)
        ][["building_id", "site_id", "primaryspaceusage", "sqm", "lat", "lng"]].copy()
        filtered_meta["site_id"] = filtered_meta["site_id"].astype(str).str.lower()

        chilled_df = pd.read_csv(chilled_path, parse_dates=["timestamp"])
        chilled_df["timestamp"] = pd.to_datetime(chilled_df["timestamp"], utc=True, errors="coerce")
        chilled_long = pd.melt(
            chilled_df,
            id_vars=["timestamp"],
            var_name="building_id",
            value_name="chilledwater_kwh",
        )

        elec_df = pd.read_csv(electricity_path, parse_dates=["timestamp"])
        elec_df["timestamp"] = pd.to_datetime(elec_df["timestamp"], utc=True, errors="coerce")
        elec_long = pd.melt(
            elec_df,
            id_vars=["timestamp"],
            var_name="building_id",
            value_name="electricity_kwh",
        )

        merged = pd.merge(
            chilled_long,
            elec_long,
            on=["timestamp", "building_id"],
            how="outer",
        )

        merged["site_id"] = merged["building_id"].astype(str).str.split("_").str[0].str.lower()
        merged["building_type"] = merged["building_id"].astype(str).str.split("_").str[1]

        valid_buildings = set(filtered_meta["building_id"].astype(str).tolist())
        merged = merged[merged["building_id"].astype(str).isin(valid_buildings)].copy()

        weather_df = pd.read_csv(weather_path, parse_dates=["timestamp"])
        weather_df["timestamp"] = pd.to_datetime(weather_df["timestamp"], utc=True, errors="coerce")
        weather_df["site_id"] = weather_df["site_id"].astype(str).str.lower()

        merged = pd.merge(
            merged,
            weather_df,
            on=["timestamp", "site_id"],
            how="left",
        )

        merged = pd.merge(
            merged,
            filtered_meta,
            on=["building_id", "site_id"],
            how="left",
        )

        merged = merged.dropna(subset=["chilledwater_kwh", "electricity_kwh"], how="all")

        out_dir = Path("data/processed")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "merged_raw.csv"
        merged.to_csv(out_file, index=False)

        logger.info("Saved merged raw dataset to {}", out_file.as_posix())
        logger.info("Merged dataset shape: {}", merged.shape)
        print(f"Merged dataset shape: {merged.shape}")
        return merged
    except Exception as exc:
        logger.exception("load_and_prepare_data failed: {}", exc)
        raise RuntimeError(f"Failed to load and prepare data: {exc}") from exc


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean missing values with controlled forward fill and weather interpolation.

    Args:
        df: Input merged dataframe.

    Returns:
        Cleaned dataframe.
    """

    try:
        before_rows = len(df)
        working = df.copy()
        working = working.sort_values(["building_id", "timestamp"]).reset_index(drop=True)

        numeric_cols = working.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            working[numeric_cols] = working.groupby("building_id")[numeric_cols].transform(
                lambda x: x.ffill(limit=3)
            )

        for col in ["airTemperature", "dewTemperature"]:
            if col in working.columns:
                working[col] = working.groupby("building_id")[col].transform(
                    lambda x: x.interpolate(method="linear", limit_direction="both")
                )

        if "cloudCoverage" in working.columns:
            working["cloudCoverage"] = working["cloudCoverage"].fillna(0)
        if "precipDepth1HR" in working.columns:
            working["precipDepth1HR"] = working["precipDepth1HR"].fillna(0)

        if "electricity_kwh" in working.columns:
            working = working.dropna(subset=["electricity_kwh"])
        if "airTemperature" in working.columns:
            working = working.dropna(subset=["airTemperature"])

        after_rows = len(working)
        dropped_pct = ((before_rows - after_rows) / before_rows * 100) if before_rows else 0.0
        logger.info(
            "Missing value handling done. Rows before: {}, after: {}, dropped: {:.2f}%",
            before_rows,
            after_rows,
            dropped_pct,
        )
        print(
            f"Rows before: {before_rows}, rows after: {after_rows}, dropped: {dropped_pct:.2f}%"
        )
        return working
    except Exception as exc:
        logger.exception("handle_missing_values failed: {}", exc)
        raise RuntimeError(f"Failed to handle missing values: {exc}") from exc


def derive_humidity_wbt_ikwtr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive relative humidity, wet bulb temperature, and iKW/TR metrics.

    Args:
        df: Cleaned dataframe with temperature and energy columns.

    Returns:
        Enriched dataframe with derived metrics.
    """

    try:
        working = df.copy()

        t = working["airTemperature"]
        td = working["dewTemperature"]
        rh = 100 * np.exp((17.625 * td) / (243.04 + td)) / np.exp((17.625 * t) / (243.04 + t))
        working["relative_humidity"] = rh.clip(0, 100)

        wbt = (
            t * np.arctan(0.151977 * np.sqrt(working["relative_humidity"] + 8.313659))
            + np.arctan(t + working["relative_humidity"])
            - np.arctan(working["relative_humidity"] - 1.676331)
            + 0.00391838
            * np.power(working["relative_humidity"], 1.5)
            * np.arctan(0.023101 * working["relative_humidity"])
            - 4.686035
        )
        working["wet_bulb_temp_c"] = wbt

        cooling_tons = working["chilledwater_kwh"] * 0.9699
        working["iKW_TR"] = working["electricity_kwh"] / cooling_tons
        working["iKW_TR"] = working["iKW_TR"].replace([np.inf, -np.inf], np.nan)
        working.loc[~working["iKW_TR"].between(0.3, 3.0), "iKW_TR"] = np.nan

        return working
    except Exception as exc:
        logger.exception("derive_humidity_wbt_ikwtr failed: {}", exc)
        raise RuntimeError(f"Failed to derive humidity/WBT/iKW_TR: {exc}") from exc


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create temporal, rolling, and categorical load features.

    Args:
        df: Input dataframe after derived metrics.

    Returns:
        Dataframe with engineered features.
    """

    try:
        working = df.copy()
        working = working.sort_values(["building_id", "timestamp"]).reset_index(drop=True)

        working["hour_of_day"] = working["timestamp"].dt.hour
        working["day_of_week"] = working["timestamp"].dt.dayofweek
        working["month"] = working["timestamp"].dt.month
        working["is_weekend"] = working["day_of_week"].isin([5, 6]).astype(int)

        working["rolling_avg_24h"] = working.groupby("building_id")["electricity_kwh"].transform(
            lambda x: x.rolling(24, min_periods=1).mean()
        )

        def categorize_load(x: pd.Series) -> pd.Series:
            """Categorize load as low/medium/high based on percentiles."""
            p33 = x.quantile(0.33)
            p66 = x.quantile(0.66)

            # If all values are the same or zero — just return 'low' for all
            if p33 == p66:
                return pd.Series(['low'] * len(x), index=x.index)

            return pd.cut(
                x,
                bins=[-float('inf'), p33, p66, float('inf')],
                labels=['low', 'medium', 'high'],
                include_lowest=True,
                duplicates='drop'  # handles any remaining edge cases
            )

        working["load_category"] = working.groupby("building_id")["electricity_kwh"].transform(
            categorize_load
        )

        return working
    except Exception as exc:
        logger.exception("engineer_features failed: {}", exc)
        raise RuntimeError(f"Failed to engineer features: {exc}") from exc


def generate_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    """
    Generate quality diagnostics for the prepared dataset.

    Args:
        df: Final feature dataframe.

    Returns:
        Dictionary with missingness, iKW/TR stats, and quality score/flag.
    """

    try:
        if len(df) == 0:
            raise ValueError("Dataframe is empty; cannot generate quality report.")

        missing_pct = (df.isnull().sum() / len(df) * 100).round(2).to_dict()
        ikwtr_valid = int(df["iKW_TR"].between(0.3, 3.0).sum())
        ikwtr_total = int(df["iKW_TR"].notna().sum())
        avg_ikwtr = round(float(df["iKW_TR"].mean()), 3) if ikwtr_total > 0 else None

        score = max(0.0, 100 - float(df.isnull().mean().mean() * 100))
        flag = "PASS" if score >= 80 else "WARN" if score >= 60 else "FAIL"

        min_ts = df["timestamp"].min()
        max_ts = df["timestamp"].max()
        date_range = {
            "start": min_ts.isoformat() if pd.notna(min_ts) else None,
            "end": max_ts.isoformat() if pd.notna(max_ts) else None,
        }

        return {
            "total_rows": int(len(df)),
            "buildings_count": int(df["building_id"].nunique()),
            "date_range": date_range,
            "missing_pct": missing_pct,
            "ikwtr_valid": ikwtr_valid,
            "ikwtr_total": ikwtr_total,
            "avg_ikwtr": avg_ikwtr,
            "quality_score": round(score, 2),
            "quality_flag": flag,
        }
    except Exception as exc:
        logger.exception("generate_quality_report failed: {}", exc)
        raise RuntimeError(f"Failed to generate quality report: {exc}") from exc

