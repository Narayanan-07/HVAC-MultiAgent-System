"""
Precompute a compact building catalogue for the dashboard dropdown.

Reads only the identifying columns from features_final.csv (not all 27),
deduplicates per building, and writes data/processed/buildings.json so the
/api/v1/buildings endpoint can serve it instantly without scanning 5.2M rows.
"""
import json
import pandas as pd

SRC = "data/processed/features_final.csv"
OUT = "data/processed/buildings.json"

cols = ["building_id", "site_id", "building_type", "primaryspaceusage", "sqm", "lat", "lng"]
df = pd.read_csv(SRC, usecols=cols)

# One row per building
agg = df.drop_duplicates(subset=["building_id"]).copy()

# Per-building iKW_TR coverage: a building can only get the full efficiency /
# anomaly analysis if it has chilled-water-derived iKW_TR values.
print("Computing iKW_TR coverage per building...")
ik = pd.read_csv(SRC, usecols=["building_id", "iKW_TR"])
cov = ik.groupby("building_id")["iKW_TR"].apply(lambda s: int(s.notna().sum())).to_dict()

buildings = []
for _, r in agg.sort_values("building_id").iterrows():
    def clean(v):
        return None if pd.isna(v) else v
    bid = str(r["building_id"])
    buildings.append({
        "building_id": bid,
        "site_id": clean(r.get("site_id")),
        "type": clean(r.get("building_type")),
        "usage": clean(r.get("primaryspaceusage")),
        "sqm": round(float(r["sqm"]), 1) if not pd.isna(r.get("sqm")) else None,
        "lat": float(r["lat"]) if not pd.isna(r.get("lat")) else None,
        "lng": float(r["lng"]) if not pd.isna(r.get("lng")) else None,
        "has_efficiency": cov.get(bid, 0) > 100,  # enough iKW_TR points to analyse
    })

analyzable = sum(1 for b in buildings if b["has_efficiency"])
print(f"  analyzable (has iKW_TR): {analyzable}/{len(buildings)}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(buildings, f, indent=2)

with_coords = sum(1 for b in buildings if b["lat"] is not None)
print(f"Wrote {len(buildings)} buildings to {OUT}")
print(f"  with coordinates: {with_coords}/{len(buildings)}")
print(f"  sample: {buildings[0]}")
