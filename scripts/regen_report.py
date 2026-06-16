"""One-off: regenerate HTML+PDF for a given run_id from on-disk task outputs."""
import sys
import sqlite3
from backend.pipeline import _ensure_report

run_id = sys.argv[1] if len(sys.argv) > 1 else "run_20260605_111113_039da7"

conn = sqlite3.connect("hvac_system.db")
row = conn.execute(
    "SELECT building_id FROM pipeline_runs WHERE run_id = ?", (run_id,)
).fetchone()
building_id = row[0] if row else "unknown"
print(f"Regenerating report for {run_id} (building={building_id})")

_ensure_report(run_id, building_id)
print("Done.")
