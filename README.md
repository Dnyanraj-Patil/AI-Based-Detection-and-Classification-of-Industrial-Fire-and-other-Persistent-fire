# ThermoIntel — SIH26162

AI-enabled geospatial thermal intelligence for detecting, contextualizing, classifying and prioritizing industrial fires and persistent thermal sources.

## One-command demo

1. Start Docker Desktop.
2. Run `RUN_THERMOINTEL.bat`.
3. Open `http://localhost:5173`.

## Pipeline

`NASA FIRMS / VIIRS → event clustering → OSM + PostGIS spatial context → persistence/thermal feature engine → source classification → fused risk intelligence → React GIS dashboard`

The implementation is aligned to SIH26162: it uses NASA FIRMS thermal detections, OSM industrial infrastructure, PostGIS spatial relationships, temporal persistence, FRP/brightness evidence, and NASA satellite thermal imagery overlays. The problem statement specifically calls for segregation of industrial fires from forest/natural fires and a GIS solution for storing and visualizing the result.

## Source classes

- Gas flare / industrial thermal source
- Industrial fire
- Wildfire / natural vegetation fire
- Agricultural burning (only when agricultural evidence exists)
- Persistent thermal source
- Other thermal source

See `CLASSIFICATION_GUIDE.md` for the exact evidence semantics and confidence definitions.

## Data coverage

The thermal-event and industrial-facility APIs do not impose the previous 1,000-event / 5,000-facility application caps. The UI loads the complete available dataset and paginates rows client-side for browser stability.

## Deployment

Docker Compose runs PostGIS, Redis, FastAPI, the India-wide OSM ingestion job, and the React/nginx dashboard. The dashboard calls the API through the nginx same-origin `/api/v1` proxy, so the deployed frontend is not tied to a developer localhost API URL.


## XGBoost source classification

ThermoIntel now uses an XGBoost multiclass classifier for source classification.
The model consumes FIRMS thermal features, temporal features, PostGIS industrial
context and WorldCover land-cover context.

Training uses human-reviewed labels from `data/ml_labels.csv` when available,
public NASA/ORNL VIIRS Nightfire flare-site labels when the optional external
dataset is downloaded, and an explainable evidence-based bootstrap for the
remaining events. This is **weak supervision**, not verified ground truth.
The system therefore reports model confidence and holdout metrics as training
diagnostics rather than claiming real-world fire-cause accuracy.

Download the public ML datasets with:

`python scripts/download_ml_datasets.py`

The previous Isolation Forest anomaly layer has been removed from the active
classification path. See `XGBOOST_MODEL_CARD.md` and `data/README.md`.

## Final XGBoost release

See `FINAL_XGBOOST_RELEASE.md` for the complete ML architecture, training-label strategy, first-run procedure and verification steps. Run `VERIFY_XGBOOST_FINAL.bat` before deployment.
