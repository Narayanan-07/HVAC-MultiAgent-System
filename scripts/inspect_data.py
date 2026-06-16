"""One-off data inspection: confirm per-building filtering feasibility."""
import pandas as pd

PROC = "data/processed/features_final.csv"
META = "data/raw/metadata.csv"

print("=" * 60)
print("FEATURES_FINAL.CSV")
print("=" * 60)
# Read only header + a small sample for columns
head = pd.read_csv(PROC, nrows=5)
print("Columns:", list(head.columns))
print()

# Unique buildings (read only the building_id column for speed)
bid = pd.read_csv(PROC, usecols=["building_id"])
counts = bid["building_id"].value_counts()
print(f"Total rows: {len(bid):,}")
print(f"Unique buildings: {bid['building_id'].nunique()}")
print("Sample buildings (top 10 by row count):")
for b, c in counts.head(10).items():
    print(f"   {b}: {c:,} rows")
print()

print("=" * 60)
print("METADATA.CSV — lat/lng availability")
print("=" * 60)
meta = pd.read_csv(META)
print("Metadata columns:", list(meta.columns))
keep = [c for c in ["building_id", "primaryspaceusage", "lat", "lng", "sqm"] if c in meta.columns]
sample_buildings = counts.head(8).index.tolist()
sub = meta[meta["building_id"].astype(str).isin([str(b) for b in sample_buildings])][keep]
print(sub.to_string(index=False))
print()
print("lat/lng non-null in metadata:",
      meta["lat"].notna().sum() if "lat" in meta.columns else "NO lat col",
      "/",
      meta["lng"].notna().sum() if "lng" in meta.columns else "NO lng col")
