"""
Standalone script to run Phase 1 data preparation.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline import run_data_preparation  # noqa: E402


def main() -> None:
    try:
        report = run_data_preparation("data/raw")
        print(json.dumps(report, indent=2, default=str))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"\nERROR: {exc}")

if __name__ == "__main__":
    main()

