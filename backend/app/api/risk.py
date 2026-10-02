from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.database import engine


router = APIRouter(
    prefix="/api/v1/risk",
    tags=["Event Risk"],
)


# ============================================================
# GET ALL RISK SCORES
# ============================================================

@router.get("")
def get_event_risk(
    limit: int = Query(default=100000, ge=1, le=100000),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
):
    """
    Return calculated event risk scores together with
    geographic and industrial context.
    """

    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="latitude and longitude must be provided together.")
    if (latitude is not None or longitude is not None) and radius_km is None:
        radius_km = 25.0
    risk_filters = []
    params = {"limit": limit}
    if latitude is not None:
        risk_filters.append("ST_DWithin(e.geom::geography, ST_SetSRID(ST_MakePoint(:longitude, :latitude),4326)::geography,:radius_meters)")
        params.update({"latitude": latitude, "longitude": longitude, "radius_meters": radius_km * 1000})
    risk_where = "WHERE " + " AND ".join(risk_filters) if risk_filters else ""

    query = text(
        f"""
        SELECT
            r.event_id,

            r.thermal_score,
            r.persistence_score,
            r.industrial_score,
            r.evidence_score,
            r.risk_score,
            r.risk_band,
            r.severity,
            r.confidence_score,
            r.classification,
            r.classification_confidence,
            r.class_probabilities,
            r.industrial_context,
            r.intelligence_reason,
            r.created_at,
            r.updated_at,
            ml.anomaly_score AS ml_anomaly_score,
            ml.normality_score AS ml_normality_score,
            ml.model_name AS ml_model_name,
            ml.model_version AS ml_model_version,
            ml.predicted_class AS ml_predicted_class,
            ml.classification_confidence AS ml_classification_confidence,
            ml.class_probabilities AS ml_class_probabilities,
            ml.training_label_source AS ml_training_label_source,

            e.first_detected_at,
            e.last_detected_at,
            e.detection_count,
            e.max_frp,
            e.average_frp,
            e.centroid_latitude,
            e.centroid_longitude,

            facility.id AS facility_id,
            facility.name AS facility_name,
            facility.facility_type,
            facility.industrial_type

        FROM processed.event_risk_scores r

        LEFT JOIN processed.thermal_events e
            ON e.id = r.event_id

        LEFT JOIN processed.event_ml_scores ml
            ON ml.event_id = r.event_id

        LEFT JOIN LATERAL (
            SELECT
                f.id,
                f.name,
                f.facility_type,
                f.industrial_type

            FROM raw.industrial_facilities f

            WHERE
                e.centroid_latitude IS NOT NULL
                AND e.centroid_longitude IS NOT NULL

                AND f.latitude IS NOT NULL
                AND f.longitude IS NOT NULL

                AND ABS(f.latitude - e.centroid_latitude) <= 0.1
                AND ABS(f.longitude - e.centroid_longitude) <= 0.1

            ORDER BY
                POWER(
                    f.latitude - e.centroid_latitude,
                    2
                )
                +
                POWER(
                    f.longitude - e.centroid_longitude,
                    2
                )

            LIMIT 1

        ) facility
            ON TRUE

        {risk_where}

        ORDER BY
            r.risk_score DESC,
            r.event_id

        LIMIT :limit
        """
    )

    try:

        with engine.connect() as connection:

            rows = (
                connection.execute(
                    query,
                    params,
                )
                .mappings()
                .all()
            )

        results = []

        for row in rows:

            latitude = (
                float(row["centroid_latitude"])
                if row["centroid_latitude"] is not None
                else None
            )

            longitude = (
                float(row["centroid_longitude"])
                if row["centroid_longitude"] is not None
                else None
            )

            # ------------------------------------------------
            # MAP LINKS
            # ------------------------------------------------

            google_maps_url = None
            openstreetmap_url = None

            if latitude is not None and longitude is not None:

                google_maps_url = (
                    f"https://www.google.com/maps/search/"
                    f"?api=1&query={latitude},{longitude}"
                )

                openstreetmap_url = (
                    f"https://www.openstreetmap.org/"
                    f"?mlat={latitude}&mlon={longitude}"
                    f"#map=16/{latitude}/{longitude}"
                )

            results.append(
                {
                    # ----------------------------------------
                    # EVENT
                    # ----------------------------------------

                    "event_id": row["event_id"],

                    # ----------------------------------------
                    # RISK
                    # ----------------------------------------

                    "thermal_score": (
                        float(row["thermal_score"])
                        if row["thermal_score"] is not None
                        else 0.0
                    ),

                    "persistence_score": (
                        float(row["persistence_score"])
                        if row["persistence_score"] is not None
                        else 0.0
                    ),

                    "industrial_score": (
                        float(row["industrial_score"])
                        if row["industrial_score"] is not None
                        else 0.0
                    ),

                    "evidence_score": (
                        float(row["evidence_score"])
                        if row["evidence_score"] is not None
                        else 0.0
                    ),

                    "risk_score": (
                        float(row["risk_score"])
                        if row["risk_score"] is not None
                        else 0.0
                    ),

                    "ml_anomaly_score": (
                        float(row["ml_anomaly_score"])
                        if row["ml_anomaly_score"] is not None
                        else None
                    ),
                    "ml_normality_score": (
                        float(row["ml_normality_score"])
                        if row["ml_normality_score"] is not None
                        else None
                    ),
                    "ml_model_name": row["ml_model_name"],
                    "ml_model_version": row["ml_model_version"],
                    "ml_predicted_class": row["ml_predicted_class"],
                    "ml_classification_confidence": (
                        float(row["ml_classification_confidence"])
                        if row["ml_classification_confidence"] is not None else None
                    ),
                    # XGBoost is a classifier, not an anomaly detector.
                    # This is the canonical score displayed by the dashboard.
                    "xgboost_score": (
                        float(row["ml_classification_confidence"])
                        if row["ml_classification_confidence"] is not None else None
                    ),
                    "ml_class_probabilities": row["ml_class_probabilities"] or {},
                    "ml_training_label_source": row["ml_training_label_source"],

                    "risk_band": row["risk_band"],

                    "severity": row["severity"],

                    "confidence_score": (
                        float(row["confidence_score"]) if row["confidence_score"] is not None else 0.0
                    ),
                    "classification": row["classification"],
                    "classification_confidence": float(row["classification_confidence"]) if row["classification_confidence"] is not None else 0.0,
                    "class_probabilities": row["class_probabilities"] or {},

                    "industrial_context": (
                        row["industrial_context"]
                    ),

                    "intelligence_reason": (
                        row["intelligence_reason"]
                    ),

                    # ----------------------------------------
                    # TIME
                    # ----------------------------------------

                    "created_at": (
                        row["created_at"].isoformat()
                        if row["created_at"]
                        else None
                    ),

                    "updated_at": (
                        row["updated_at"].isoformat()
                        if row["updated_at"]
                        else None
                    ),

                    "first_detected_at": (
                        row["first_detected_at"].isoformat()
                        if row["first_detected_at"]
                        else None
                    ),

                    "last_detected_at": (
                        row["last_detected_at"].isoformat()
                        if row["last_detected_at"]
                        else None
                    ),

                    # ----------------------------------------
                    # THERMAL INFORMATION
                    # ----------------------------------------

                    "detection_count": (
                        row["detection_count"]
                    ),

                    "max_frp": (
                        float(row["max_frp"])
                        if row["max_frp"] is not None
                        else None
                    ),

                    "average_frp": (
                        float(row["average_frp"])
                        if row["average_frp"] is not None
                        else None
                    ),

                    # ----------------------------------------
                    # LOCATION
                    # ----------------------------------------

                    "latitude": latitude,

                    "longitude": longitude,

                    # ----------------------------------------
                    # INDUSTRIAL FACILITY
                    # ----------------------------------------

                    "facility_id": (
                        row["facility_id"]
                        if row["facility_id"] is not None
                        else None
                    ),

                    "facility_name": (
                        row["facility_name"]
                        if row["facility_name"]
                        else None
                    ),

                    "facility_type": (
                        row["facility_type"]
                        if row["facility_type"]
                        else None
                    ),

                    "industrial_type": (
                        row["industrial_type"]
                        if row["industrial_type"]
                        else None
                    ),

                    # ----------------------------------------
                    # MAP LINKS
                    # ----------------------------------------

                    "google_maps_url": google_maps_url,

                    "openstreetmap_url": openstreetmap_url,
                }
            )

        return {
            "count": len(results),
            "risk_scores": results,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event risk scores.",
        ) from exc


# ============================================================
# RISK SUMMARY
# ============================================================

@router.get("/summary")
def get_risk_summary():
    """
    Return event risk distribution and statistics.
    """

    query = text(
        """
        SELECT
            COUNT(*) AS total_events,

            COUNT(*) FILTER (
                WHERE risk_band = 'CRITICAL'
            ) AS critical_events,

            COUNT(*) FILTER (
                WHERE risk_band = 'HIGH'
            ) AS high_events,

            COUNT(*) FILTER (
                WHERE risk_band = 'MODERATE'
            ) AS moderate_events,

            COUNT(*) FILTER (
                WHERE risk_band = 'LOW'
            ) AS low_events,

            AVG(risk_score) AS average_risk_score,

            MAX(risk_score) AS maximum_risk_score

        FROM processed.event_risk_scores r
        JOIN processed.thermal_events e
            ON e.id = r.event_id
        """
    )

    try:

        with engine.connect() as connection:

            row = (
                connection.execute(query)
                .mappings()
                .one()
            )

        return {
            "total_events": row["total_events"],

            "critical_events": row["critical_events"],

            "high_events": row["high_events"],

            "moderate_events": row["moderate_events"],

            "low_events": row["low_events"],

            "average_risk_score": (
                float(row["average_risk_score"])
                if row["average_risk_score"] is not None
                else None
            ),

            "maximum_risk_score": (
                float(row["maximum_risk_score"])
                if row["maximum_risk_score"] is not None
                else None
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail="Unable to generate risk summary.",
        ) from exc


# ============================================================
# GET RISK FOR ONE EVENT
# ============================================================

@router.get("/{event_id}")
def get_event_risk_by_id(
    event_id: int,
):
    """
    Return risk assessment and location information
    for one thermal event.
    """

    query = text(
        """
        SELECT
            r.event_id,

            r.thermal_score,
            r.persistence_score,
            r.industrial_score,
            r.evidence_score,
            r.risk_score,
            r.risk_band,
            r.severity,
            r.confidence_score,
            r.industrial_context,
            r.intelligence_reason,
            r.created_at,
            r.updated_at,

            e.centroid_latitude,
            e.centroid_longitude,
            e.first_detected_at,
            e.last_detected_at,
            e.detection_count,
            e.max_frp,
            e.average_frp,

            facility.id AS facility_id,
            facility.name AS facility_name,
            facility.facility_type,
            facility.industrial_type

        FROM processed.event_risk_scores r

        LEFT JOIN processed.thermal_events e
            ON e.id = r.event_id

        LEFT JOIN processed.event_ml_scores ml
            ON ml.event_id = r.event_id

        LEFT JOIN LATERAL (
            SELECT
                f.id,
                f.name,
                f.facility_type,
                f.industrial_type

            FROM raw.industrial_facilities f

            WHERE
                e.centroid_latitude IS NOT NULL
                AND e.centroid_longitude IS NOT NULL

                AND f.latitude IS NOT NULL
                AND f.longitude IS NOT NULL

                AND ABS(f.latitude - e.centroid_latitude) <= 0.1
                AND ABS(f.longitude - e.centroid_longitude) <= 0.1

            ORDER BY
                POWER(
                    f.latitude - e.centroid_latitude,
                    2
                )
                +
                POWER(
                    f.longitude - e.centroid_longitude,
                    2
                )

            LIMIT 1

        ) facility
            ON TRUE

        WHERE r.event_id = :event_id
        """
    )

    try:

        with engine.connect() as connection:

            row = (
                connection.execute(
                    query,
                    {"event_id": event_id},
                )
                .mappings()
                .one_or_none()
            )

        if row is None:

            raise HTTPException(
                status_code=404,
                detail="Event risk score not found.",
            )

        latitude = (
            float(row["centroid_latitude"])
            if row["centroid_latitude"] is not None
            else None
        )

        longitude = (
            float(row["centroid_longitude"])
            if row["centroid_longitude"] is not None
            else None
        )

        google_maps_url = None
        openstreetmap_url = None

        if latitude is not None and longitude is not None:

            google_maps_url = (
                f"https://www.google.com/maps/search/"
                f"?api=1&query={latitude},{longitude}"
            )

            openstreetmap_url = (
                f"https://www.openstreetmap.org/"
                f"?mlat={latitude}&mlon={longitude}"
                f"#map=16/{latitude}/{longitude}"
            )

        return {
            "event_id": row["event_id"],

            "thermal_score": float(
                row["thermal_score"]
            ),

            "persistence_score": float(
                row["persistence_score"]
            ),

            "industrial_score": float(
                row["industrial_score"]
            ),

            "evidence_score": float(
                row["evidence_score"]
            ),

            "risk_score": float(
                row["risk_score"]
            ),

            "risk_band": row["risk_band"],

            "severity": row["severity"],

            "confidence_score": float(
                row["confidence_score"]
            ),

            "industrial_context": (
                row["industrial_context"]
            ),

            "intelligence_reason": (
                row["intelligence_reason"]
            ),

            "created_at": (
                row["created_at"].isoformat()
                if row["created_at"]
                else None
            ),

            "updated_at": (
                row["updated_at"].isoformat()
                if row["updated_at"]
                else None
            ),

            "first_detected_at": (
                row["first_detected_at"].isoformat()
                if row["first_detected_at"]
                else None
            ),

            "last_detected_at": (
                row["last_detected_at"].isoformat()
                if row["last_detected_at"]
                else None
            ),

            "detection_count": row["detection_count"],

            "max_frp": (
                float(row["max_frp"])
                if row["max_frp"] is not None
                else None
            ),

            "average_frp": (
                float(row["average_frp"])
                if row["average_frp"] is not None
                else None
            ),

            # Location
            "latitude": latitude,
            "longitude": longitude,

            # Facility
            "facility_id": (
                row["facility_id"]
                if row["facility_id"] is not None
                else None
            ),

            "facility_name": (
                row["facility_name"]
                if row["facility_name"]
                else None
            ),

            "facility_type": (
                row["facility_type"]
                if row["facility_type"]
                else None
            ),

            "industrial_type": (
                row["industrial_type"]
                if row["industrial_type"]
                else None
            ),

            # Maps
            "google_maps_url": google_maps_url,
            "openstreetmap_url": openstreetmap_url,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event risk score.",
        ) from exc