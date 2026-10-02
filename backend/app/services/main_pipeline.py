from app.services.event_clustering import cluster_firms_events
from app.services.event_repository import save_thermal_events
from app.services.landcover_service import process_recent_landcover
from app.services.industrial_context_service import process_all_event_industrial_context
from app.services.event_intelligence_service import process_all_event_intelligence
from app.services.event_risk_service import process_all_event_risk
from app.services.xgboost_classifier_service import train_or_refresh_ml_model


def run_pipeline_sync(force_landcover=False):
    events = cluster_firms_events()
    saved = save_thermal_events(events)
    context = process_all_event_industrial_context()
    land = process_recent_landcover(force=force_landcover)
    ml = train_or_refresh_ml_model()
    intel = process_all_event_intelligence()
    risk = process_all_event_risk()
    return {
        "thermal_events": saved,
        "industrial_context": context,
        "land_cover": land,
        "ml_anomaly": ml,
        "ml_xgboost": ml,
        "event_intelligence": intel,
        "risk_events": len(risk),
    }
