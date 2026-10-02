"""Single-command ThermoIntel XGBoost evaluation.

Ground-truth evaluation:
  - Uses only human-reviewed labels in data/ml_labels.csv as the test set.
  - Excludes those event IDs from training.
  - Trains a fresh XGBoost model on the remaining ThermoIntel events using
    the project's bootstrap/external-label strategy.
  - Reports accuracy, balanced accuracy, precision, recall, F1, per-class
    metrics, confusion matrix, and sample counts.

If there are no reviewed labels, the script does NOT invent an accuracy.
It reports the model's internal weak-label holdout metrics separately and
clearly marks them as non-ground-truth.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    f1_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.xgboost_classifier_service import (  # noqa: E402
    CLASSES,
    FEATURE_NAMES,
    _fetch_rows,
    _training_matrix,
    _row_features,
    _weak_label,
    MIN_CLASS_SAMPLES,
)

LABELS_FILE = ROOT / "data" / "ml_labels.csv"
REPORT_DIR = ROOT / "reports"
REPORT_JSON = REPORT_DIR / "xgboost_complete_evaluation.json"
REPORT_TXT = REPORT_DIR / "xgboost_complete_evaluation.txt"


def load_reviewed_labels():
    result = {}
    if not LABELS_FILE.exists():
        return result
    with LABELS_FILE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            event_id = str(row.get("event_id") or "").strip()
            label = str(row.get("label") or row.get("reviewed_label") or "").strip().upper()
            if event_id and label in CLASSES:
                result[event_id] = label
    return result


def make_model(n_classes):
    return XGBClassifier(
        objective="multi:softprob",
        num_class=n_classes,
        n_estimators=320,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.90,
        colsample_bytree=0.90,
        reg_lambda=1.5,
        reg_alpha=0.1,
        min_child_weight=2,
        tree_method="hist",
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=4,
    )


def evaluate(y_true, y_pred, title, sample_count, labels=CLASSES):
    report = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    return {
        "title": title,
        "evaluated_samples": int(sample_count),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_precision": float(report["macro avg"]["precision"]),
        "macro_recall": float(report["macro avg"]["recall"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "weighted_f1": float(report["weighted avg"]["f1-score"]),
        "per_class": {
            cls: {
                "precision": float(p[i]),
                "recall": float(r[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, cls in enumerate(labels)
        },
        "confusion_matrix_labels": list(labels),
        "confusion_matrix": cm,
    }


def print_metrics(m, ground_truth):
    print("\n" + m["title"])
    print("=" * len(m["title"]))
    print(f"Evaluation samples:     {m['evaluated_samples']}")
    print(f"Accuracy:               {m['accuracy'] * 100:.2f}%")
    print(f"Balanced accuracy:      {m['balanced_accuracy'] * 100:.2f}%")
    print(f"Macro precision:        {m['macro_precision'] * 100:.2f}%")
    print(f"Macro recall:           {m['macro_recall'] * 100:.2f}%")
    print(f"Macro F1:               {m['macro_f1'] * 100:.2f}%")
    print(f"Weighted F1:            {m['weighted_f1'] * 100:.2f}%")
    if ground_truth:
        print("STATUS: VERIFIED HUMAN-REVIEWED TEST SET")
    else:
        print("STATUS: WEAK-LABEL INTERNAL VALIDATION — NOT GROUND TRUTH")
    print("\nPer-class metrics:")
    for cls, values in m["per_class"].items():
        if values["support"]:
            print(
                f"  {cls:42s} P={values['precision']*100:6.2f}% "
                f"R={values['recall']*100:6.2f}% F1={values['f1']*100:6.2f}% "
                f"N={values['support']}"
            )
    print("\nConfusion matrix (rows=true, columns=predicted):")
    print("  " + " | ".join(f"{c[:8]:>8}" for c in CLASSES))
    for cls, row in zip(CLASSES, m["confusion_matrix"]):
        print(f"  {cls[:8]:>8} " + " | ".join(f"{v:8d}" for v in row))


def weak_internal_evaluation(rows):
    X, y, ids, coords, sources = _training_matrix(rows)
    if len(y) < 40:
        return None, {"reason": f"Only {len(y)} usable training examples; need at least 40."}
    counts = np.bincount(y, minlength=len(CLASSES))
    active = [i for i, c in enumerate(counts) if c >= MIN_CLASS_SAMPLES]
    if len(active) < 2:
        return None, {"reason": "Fewer than two classes have five examples each."}
    keep = np.isin(y, active)
    X, y = X[keep], y[keep]
    coords = [v for v, k in zip(coords, keep) if k]
    global_to_local = {g: i for i, g in enumerate(active)}
    y_local = np.array([global_to_local[int(v)] for v in y], dtype=np.int64)
    groups = np.array([f"{math.floor(a/0.5)}:{math.floor(b/0.5)}" for a,b in coords])
    unique = np.unique(groups)
    if len(unique) >= 6:
        test_groups = set(unique[::5])
        test_mask = np.array([g in test_groups for g in groups])
        if test_mask.sum() < max(10, int(len(y)*0.1)):
            test_mask = None
    else:
        test_mask = None
    if test_mask is None:
        idx = np.arange(len(y_local))
        try:
            _, test_idx = train_test_split(idx, test_size=0.2, random_state=42, stratify=y_local)
        except ValueError:
            _, test_idx = train_test_split(idx, test_size=0.2, random_state=42)
        test_mask = np.zeros(len(y_local), dtype=bool)
        test_mask[test_idx] = True
    train_mask = ~test_mask
    model = make_model(len(active))
    weights = np.asarray([1.0 / max(counts[active[int(v)]], 1) ** 0.5 for v in y_local[train_mask]], dtype=np.float32)
    model.fit(X[train_mask], y_local[train_mask], sample_weight=weights)
    pred_local = model.predict(X[test_mask]).reshape(-1).astype(int)
    pred_global = np.array([active[int(v)] for v in pred_local], dtype=np.int64)
    metrics = evaluate(y[test_mask], pred_global, "XGBoost Internal Validation", int(test_mask.sum()))
    return metrics, {"training_examples": int(train_mask.sum()), "test_examples": int(test_mask.sum()), "active_classes": [CLASSES[i] for i in active]}


def main():
    print("=" * 72)
    print("ThermoIntel — COMPLETE XGBOOST ACCURACY / PRECISION / RECALL REPORT")
    print("=" * 72)
    print("This evaluator never treats XGBoost confidence as accuracy.\n")

    reviewed = load_reviewed_labels()
    rows = _fetch_rows()
    by_id = {str(r["id"]): r for r in rows}

    unknown = sorted(set(reviewed.values()) - set(CLASSES))
    if unknown:
        raise SystemExit(f"Unknown reviewed labels: {unknown}")

    internal, internal_meta = weak_internal_evaluation(rows)
    if internal:
        print_metrics(internal, ground_truth=False)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_policy": "Human-reviewed event IDs are a held-out test set and are excluded from training.",
        "ground_truth_test": None,
        "internal_weak_validation": internal,
        "internal_validation_meta": internal_meta,
        "reviewed_label_count": len(reviewed),
    }

    if reviewed:
        selected = [r for r in rows if str(r["id"]) in reviewed]
        missing = sorted(set(reviewed) - {str(r["id"]) for r in selected})
        if len(selected) < 20:
            print("\nGROUND-TRUTH TEST SET")
            print("=====================")
            print(f"Reviewed labels found: {len(selected)}")
            print("A defensible percentage requires at least 20 reviewed events in this evaluator.")
            print("Add more human-reviewed labels to data/ml_labels.csv and rerun.")
        elif len({reviewed[str(r["id"])] for r in selected}) < 2:
            print("\nGROUND-TRUTH TEST SET")
            print("=====================")
            print("Need at least two represented classes in the reviewed test set.")
        else:
            # Build weak/external training data and remove ALL reviewed IDs so the
            # reported test set is genuinely unseen by the freshly trained model.
            train_rows = [r for r in rows if str(r["id"]) not in reviewed]
            X, y, ids, coords, sources = _training_matrix(train_rows)
            if len(y) < 40:
                print("\nGROUND-TRUTH TEST SET")
                print("=====================")
                print("Not enough non-reviewed training examples to train a fresh evaluation model.")
            else:
                counts = np.bincount(y, minlength=len(CLASSES))
                active = [i for i,c in enumerate(counts) if c >= MIN_CLASS_SAMPLES]
                if len(active) < 2:
                    print("\nGROUND-TRUTH TEST SET")
                    print("=====================")
                    print("Training data does not contain two sufficiently represented classes.")
                else:
                    keep = np.isin(y, active)
                    X, y = X[keep], y[keep]
                    global_to_local = {g:i for i,g in enumerate(active)}
                    y_local = np.array([global_to_local[int(v)] for v in y], dtype=np.int64)
                    test_X = np.asarray([_row_features(r) for r in selected], dtype=np.float32)
                    y_true = np.array([CLASSES.index(reviewed[str(r["id"])]) for r in selected], dtype=np.int64)
                    model = make_model(len(active))
                    weights = np.asarray([1.0 / max(counts[active[int(v)]],1)**0.5 for v in y_local], dtype=np.float32)
                    model.fit(X, y_local, sample_weight=weights)
                    pred_local = model.predict(test_X).reshape(-1).astype(int)
                    pred_global = np.array([active[int(v)] if int(v) < len(active) else active[-1] for v in pred_local], dtype=np.int64)
                    gt = evaluate(y_true, pred_global, "XGBoost HUMAN-REVIEWED HELD-OUT TEST", len(selected))
                    gt["missing_reviewed_event_ids"] = missing
                    gt["training_examples"] = int(len(y))
                    gt["active_training_classes"] = [CLASSES[i] for i in active]
                    result["ground_truth_test"] = gt
                    print_metrics(gt, ground_truth=True)
                    if missing:
                        print(f"WARNING: {len(missing)} reviewed IDs are not in the current database.")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "ThermoIntel XGBoost Evaluation Report",
        f"Generated: {result['generated_at']}",
        "",
        "GROUND-TRUTH POLICY: Human-reviewed events are excluded from training and evaluated as a held-out test set.",
        "",
    ]
    if result["ground_truth_test"]:
        g = result["ground_truth_test"]
        lines += [
            "HUMAN-REVIEWED HELD-OUT TEST",
            f"Samples: {g['evaluated_samples']}",
            f"Accuracy: {g['accuracy']*100:.2f}%",
            f"Balanced accuracy: {g['balanced_accuracy']*100:.2f}%",
            f"Macro precision: {g['macro_precision']*100:.2f}%",
            f"Macro recall: {g['macro_recall']*100:.2f}%",
            f"Macro F1: {g['macro_f1']*100:.2f}%",
            f"Weighted F1: {g['weighted_f1']*100:.2f}%",
            "",
        ]
    else:
        lines += [
            "HUMAN-REVIEWED HELD-OUT TEST: NOT AVAILABLE",
            "Do not report the weak-label internal validation as real-world accuracy.",
            "Add human-reviewed labels to data/ml_labels.csv and rerun.",
            "",
        ]
    if internal:
        lines += [
            "INTERNAL WEAK-LABEL VALIDATION (NOT GROUND TRUTH)",
            f"Samples: {internal['evaluated_samples']}",
            f"Accuracy: {internal['accuracy']*100:.2f}%",
            f"Balanced accuracy: {internal['balanced_accuracy']*100:.2f}%",
            f"Macro precision: {internal['macro_precision']*100:.2f}%",
            f"Macro recall: {internal['macro_recall']*100:.2f}%",
            f"Macro F1: {internal['macro_f1']*100:.2f}%",
        ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nFull JSON report: {REPORT_JSON}")
    print(f"Text report:      {REPORT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
