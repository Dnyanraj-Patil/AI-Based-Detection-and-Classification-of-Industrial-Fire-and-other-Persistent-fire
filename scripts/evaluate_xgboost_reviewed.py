"""Evaluate ThermoIntel XGBoost on HUMAN-REVIEWED labels only.

Usage from project root:
    python scripts/evaluate_xgboost_reviewed.py

The script deliberately refuses to call weak/evidence labels "ground truth".
Add reviewed rows to data/ml_labels.csv before reporting these metrics.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))



LABELS_FILE = ROOT / "data" / "ml_labels.csv"

def load_reviewed_labels():
    if not LABELS_FILE.exists():
        return {}
    labels = {}
    with LABELS_FILE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = (row.get("label") or row.get("reviewed_label") or "").strip().upper()
            event_id = (row.get("event_id") or "").strip()
            if event_id and label:
                labels[event_id] = label
    return labels


def main():
    reviewed = load_reviewed_labels()
    if not reviewed:
        print("NO VALID ACCURACY RESULT")
        print("data/ml_labels.csv contains no human-reviewed labels.")
        print("Do NOT report the XGBoost confidence as accuracy.")
        print("Label events first, then rerun this script.")
        return 2

    # Import the DB-backed model service only after confirming that reviewed
    # ground-truth labels actually exist. This lets the script give a useful
    # message on a fresh machine without a configured PostgreSQL connection.
    from app.services.xgboost_classifier_service import (
        CLASSES, FEATURE_NAMES, LABELS_PATH, MODEL_PATH, _fetch_rows, _row_features
    )
    from xgboost import XGBClassifier

    unknown = sorted(set(reviewed.values()) - set(CLASSES))
    if unknown:
        raise SystemExit(f"Unknown labels in ml_labels.csv: {unknown}\nAllowed: {CLASSES}")

    if not MODEL_PATH.exists():
        print("NO VALID ACCURACY RESULT")
        print(f"Model not found: {MODEL_PATH}")
        print("Run the ThermoIntel pipeline once to train XGBoost, then rerun.")
        return 2

    rows = _fetch_rows()
    selected = [r for r in rows if str(r["id"]) in reviewed]
    missing = sorted(set(reviewed) - {str(r["id"]) for r in selected})
    if not selected:
        print("NO VALID ACCURACY RESULT")
        print("Reviewed event IDs were not found in the current database.")
        return 2

    model = XGBClassifier()
    model.load_model(str(MODEL_PATH))
    X = [_row_features(r) for r in selected]
    y_true = [reviewed[str(r["id"])] for r in selected]
    local_pred = model.predict(X).reshape(-1).astype(int)
    model_classes = list(getattr(model, "classes_", range(len(CLASSES))))
    # XGBoost stores local class indexes for the active classes. The JSON model
    # does not carry ThermoIntel's global names, so map via active class names
    # from metrics when available.
    metrics_path = MODEL_PATH.with_name("thermointel_xgboost_metrics.json")
    active_names = CLASSES
    if metrics_path.exists():
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
            active_names = payload.get("active_classes_names") or payload.get("active_classes") or CLASSES
        except Exception:
            pass
    if all(isinstance(v, int) for v in active_names):
        active_names = [CLASSES[int(v)] for v in active_names]
    y_pred = [active_names[int(p)] if int(p) < len(active_names) else "OTHER THERMAL SOURCE" for p in local_pred]

    accuracy = accuracy_score(y_true, y_pred)
    balanced = balanced_accuracy_score(y_true, y_pred)
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    report = classification_report(y_true, y_pred, labels=CLASSES, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES).tolist()

    out = ROOT / "reports" / "xgboost_reviewed_evaluation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "evaluation_type": "HUMAN_REVIEWED_LABELS",
        "ground_truth": True,
        "model_path": str(MODEL_PATH.relative_to(ROOT)),
        "reviewed_samples_available": len(reviewed),
        "evaluated_samples": len(selected),
        "missing_event_ids": missing,
        "accuracy": round(float(accuracy), 4),
        "accuracy_percent": round(float(accuracy * 100), 2),
        "balanced_accuracy": round(float(balanced), 4),
        "balanced_accuracy_percent": round(float(balanced * 100), 2),
        "macro_precision": round(float(report["macro avg"]["precision"]), 4),
        "macro_recall": round(float(report["macro avg"]["recall"]), 4),
        "macro_f1": round(float(report["macro avg"]["f1-score"]), 4),
        "per_class": {
            cls: {
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f1[i]), 4),
                "support": int(support[i]),
            }
            for i, cls in enumerate(CLASSES)
        },
        "confusion_matrix_labels": CLASSES,
        "confusion_matrix": cm,
        "classification_report": report,
        "feature_names": FEATURE_NAMES,
    }
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("ThermoIntel XGBoost — HUMAN-REVIEWED EVALUATION")
    print("=" * 54)
    print(f"Evaluated samples:     {len(selected)}")
    print(f"Accuracy:              {accuracy * 100:.2f}%")
    print(f"Balanced accuracy:     {balanced * 100:.2f}%")
    print(f"Macro precision:       {report['macro avg']['precision'] * 100:.2f}%")
    print(f"Macro recall:          {report['macro avg']['recall'] * 100:.2f}%")
    print(f"Macro F1:              {report['macro avg']['f1-score'] * 100:.2f}%")
    print(f"Saved report:          {out}")
    if missing:
        print(f"WARNING: {len(missing)} reviewed event IDs are not in the current database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
