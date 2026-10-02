# ThermoIntel Final XGBoost Fixes

## Event details
Opening `/api/v1/events/{event_id}/context` now refreshes the clicked event's contextual intelligence and risk record using the current XGBoost result. The probable-cause panel therefore does not remain stuck on the generic processing message when a derived row was missing or stale.

## XGBoost score
XGBoost is a multiclass classifier. Its `classification_confidence` is the canonical XGBoost score shown in the UI. The legacy `anomaly_score` remains in the database only for backward schema compatibility and is not presented as XGBoost confidence.

## Existing databases
The classifier version is now `1.1`. A previous model version or a zero-confidence row is automatically refreshed by the next derived pipeline run or when an affected event is opened.

## Pipeline consistency
The intelligence refresh detects changes to `event_ml_scores.updated_at`, so newly generated XGBoost predictions cause event intelligence and risk intelligence to be recalculated.
