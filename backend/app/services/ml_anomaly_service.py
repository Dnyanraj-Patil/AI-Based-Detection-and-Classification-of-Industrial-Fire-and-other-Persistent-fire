"""Compatibility wrapper for the previous ML anomaly service.

ThermoIntel now uses XGBoost for supervised/weakly-supervised source
classification.  The old import path remains available so existing API code
and integrations do not break.
"""
from app.services.xgboost_classifier_service import (
    train_or_refresh_ml_model,
    get_ml_score,
    get_ml_summary,
    get_ml_classification,
)
