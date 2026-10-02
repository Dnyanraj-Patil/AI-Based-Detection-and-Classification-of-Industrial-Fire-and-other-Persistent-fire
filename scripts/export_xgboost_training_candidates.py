"""Export ThermoIntel events into a reviewable XGBoost training CSV.

This is useful for human labeling. It never marks the exported weak labels as
ground truth.
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.xgboost_classifier_service import _fetch_rows, _weak_label, CLASSES


def main():
    out = ROOT / "data" / "xgboost_training_candidates.csv"
    rows = _fetch_rows()
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "event_id", "latitude", "longitude", "max_frp", "max_bright_ti4",
            "detection_count", "duration_minutes", "facility_distance_m",
            "land_cover_class", "weak_label", "weak_confidence", "reviewed_label"
        ])
        for row in rows:
            label, confidence = _weak_label(row)
            writer.writerow([
                row["id"], row["latitude"], row["longitude"], row["max_frp"],
                row["max_bright_ti4"], row["detection_count"],
                row["observation_duration_minutes"], row["facility_distance"],
                row["land_cover_class"], label, round(confidence, 4), ""
            ])
    print(out)


if __name__ == "__main__":
    main()
