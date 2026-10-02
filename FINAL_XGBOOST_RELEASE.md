# ThermoIntel — Final XGBoost Release

## ML architecture

Isolation Forest has been removed from the active ML implementation. ThermoIntel now uses an XGBoost multiclass source classifier with thermal, temporal, industrial-context, land-cover and geographic features.

The existing evidence/rule classifier remains as an explainable guardrail. It is not presented as ground truth. XGBoost is the primary ML source classifier when a trained model is available and its prediction satisfies the context guardrails.

## Classes

- INDUSTRIAL FIRE
- GAS FLARE / INDUSTRIAL THERMAL SOURCE
- FOREST / VEGETATION FIRE
- AGRICULTURAL BURNING
- PERSISTENT THERMAL SOURCE
- OTHER THERMAL SOURCE

## Training labels

The training pipeline uses, in priority order:

1. Human-reviewed labels in `data/ml_labels.csv`.
2. Public NASA/ORNL VIIRS Nightfire flare-site coordinates when the optional dataset is installed.
3. Explainable weak-supervision labels derived from the existing ThermoIntel evidence features.

Weak-supervision metrics are explicitly marked as **not ground-truth accuracy**.

## First run

1. Copy `.env.example` to `.env`.
2. Put your NASA FIRMS `FIRMS_MAP_KEY` in `.env`.
3. Run `DOWNLOAD_ML_DATASETS.bat` when internet access is available. The FIRMS sample and ORNL flare survey are optional supporting datasets; operational FIRMS ingestion still uses your MAP key.
4. Run `RUN_THERMOINTEL.bat` or `docker compose up -d --build`.
5. The pipeline ingests FIRMS, clusters events, enriches industrial context, processes land cover, trains/refreshes XGBoost, then writes intelligence and risk results.
6. The model is trained once there are at least 40 usable events and at least two classes with five usable examples each.

The trained model is stored in `backend/models/` and persisted through the Docker volume mapping.

## Verification

Run `VERIFY_XGBOOST_FINAL.bat` on Windows. It checks Python compilation, XGBoost availability, and confirms that Isolation Forest is not present in the active classifier.

## Important model limitation

Satellite thermal detections do not independently prove physical cause. The XGBoost confidence is model confidence, not a calibrated probability that a physical cause is true. For serious evaluation, populate `data/ml_labels.csv` with reviewed event labels and evaluate on a geographically separated, human-verified test set.
