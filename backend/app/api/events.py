from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.database import engine
from app.services.industrial_context_service import (
    calculate_event_industrial_context,
    save_event_industrial_context,
)
from app.services.event_intelligence_service import (
    _classify_source,
    classify_event,
    save_event_intelligence,
)
from app.services.event_risk_service import process_event_risk


router = APIRouter(
    prefix="/api/v1/events",
    tags=["Thermal Events"],
)


def normalize_detection_confidence(value):
    """Normalize NASA FIRMS categorical confidence for display."""
    if value is None:
        return "Unknown"
    normalized = str(value).strip().lower()
    return {
        "l": "Low",
        "n": "Nominal",
        "h": "High",
    }.get(normalized, str(value))



# ============================================================
# THERMAL EVENT CLASSIFICATION
# ============================================================

# The canonical classifier lives in event_intelligence_service.
# This compatibility helper is retained for callers that need a label
# before the intelligence pipeline has produced a row.
def classify_thermal_event(
    max_frp,
    max_bright_ti4,
    detection_count,
    nearest_facility_id=None,
    is_inside_industrial_area=False,
    nearest_facility_name=None,
    nearest_facility_type=None,
    nearest_industrial_type=None,
    observation_duration_minutes=0,
):
    """Compatibility fallback using the same source classifier as the pipeline."""
    event = {
        "max_frp": max_frp,
        "max_bright_ti4": max_bright_ti4,
        "detection_count": detection_count,
        "observation_duration_minutes": observation_duration_minutes,
    }
    context = {
        "nearest_facility_id": nearest_facility_id,
        "is_inside_industrial_area": is_inside_industrial_area,
        "nearest_facility_distance_meters": 0 if nearest_facility_id else None,
        "nearest_facility_name": nearest_facility_name,
        "nearest_facility_type": nearest_facility_type,
        "nearest_industrial_type": nearest_industrial_type,
    }
    classification, _, _ = _classify_source(event, context)
    return classification


# ============================================================
# CURRENT PROCESSED THERMAL EVENTS
# ============================================================

@router.get("")
def get_events(
    limit: int | None = Query(default=None, ge=1, le=100000),
    window_hours: int | None = Query(
        default=None, ge=1, description="Optional rolling window in hours."
    ),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
):
    """
    Return the canonical ThermoIntel thermal-event dataset.

    LIVE:
        No window_hours parameter.
        Returns all available processed thermal events.

    Rolling windows:
        window_hours=24  -> last 24 hours
        window_hours=72  -> last 3 days
        window_hours=168 -> last 7 days

    The dashboard and event feed therefore use the same
    canonical processed.thermal_events population.
    """

    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="latitude and longitude must be provided together.")
    if (latitude is not None or longitude is not None) and radius_km is None:
        radius_km = 25.0

    params = {}
    limit_clause = ""
    if limit is not None:
        params["limit"] = limit
        limit_clause = "LIMIT :limit"

    window_filter = ""

    conditions = []
    if window_hours is not None:
        conditions.append("e.last_detected_at >= (CURRENT_TIMESTAMP - (:window_hours * INTERVAL '1 hour'))")
        params["window_hours"] = window_hours
    if latitude is not None:
        conditions.append("ST_DWithin(e.geom::geography, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography, :radius_meters)")
        params.update({"latitude": latitude, "longitude": longitude, "radius_meters": radius_km * 1000})
    if conditions:
        window_filter = "WHERE " + " AND ".join(conditions)

    query = text(
        f"""
        SELECT
            e.id,
            e.centroid_latitude AS latitude,
            e.centroid_longitude AS longitude,
            e.first_detected_at,
            e.last_detected_at,
            e.detection_count,
            e.observation_duration_minutes,
            e.max_frp,
            e.average_frp,
            e.max_bright_ti4,
            e.average_bright_ti4,
            e.satellites,

            rep.satellite,
            rep.instrument,
            rep.bright_ti5,
            rep.confidence,
            rep.daynight,
            rep.version,
            rep.source,

            c.nearest_facility_id,
            c.nearest_facility_name,
            c.nearest_facility_type,
            c.nearest_industrial_type,
            c.nearest_facility_distance_meters,
            c.facilities_within_1km,
            c.is_inside_industrial_area,
            r.risk_score,
            r.risk_band,
            i.classification,
            i.classification_confidence,
            i.confidence_score AS intelligence_confidence,
            ml.anomaly_score AS ml_anomaly_score,
            ml.normality_score AS ml_normality_score,
            ml.model_name AS ml_model_name,
            ml.model_version AS ml_model_version,
            ml.predicted_class AS ml_predicted_class,
            ml.classification_confidence AS ml_classification_confidence,
            ml.class_probabilities AS ml_class_probabilities,
            ml.training_label_source AS ml_training_label_source

        FROM processed.thermal_events e

        LEFT JOIN processed.event_industrial_context c
            ON c.event_id = e.id

        LEFT JOIN processed.event_risk_scores r
            ON r.event_id = e.id

        LEFT JOIN processed.event_intelligence i
            ON i.event_id = e.id

        LEFT JOIN processed.event_ml_scores ml
            ON ml.event_id = e.id

        LEFT JOIN LATERAL (
            SELECT
                f.satellite,
                f.instrument,
                f.bright_ti5,
                f.confidence,
                f.daynight,
                f.version,
                f.source

            FROM processed.thermal_event_detections m

            JOIN raw.firms_events f
                ON f.id = m.firms_event_id

            WHERE m.event_id = e.id

            ORDER BY
                f.frp DESC NULLS LAST,
                f.acquisition_datetime DESC

            LIMIT 1
        ) rep ON TRUE

        {window_filter}

        ORDER BY
            e.last_detected_at DESC,
            e.id DESC

        {limit_clause}
        """
    )

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                query,
                params,
            ).mappings().all()

        events = []

        for row in rows:
            events.append(
                {
                    "id": row["id"],

                    "latitude": (
                        float(row["latitude"])
                        if row["latitude"] is not None
                        else None
                    ),

                    "longitude": (
                        float(row["longitude"])
                        if row["longitude"] is not None
                        else None
                    ),

                    "acquisition_datetime": (
                        row["last_detected_at"].isoformat()
                        if row["last_detected_at"]
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

                    "satellite": row["satellite"],
                    "satellites": row["satellites"],
                    "instrument": row["instrument"],

                    "bright_ti4": (
                        float(row["max_bright_ti4"])
                        if row["max_bright_ti4"] is not None
                        else None
                    ),

                    "bright_ti5": (
                        float(row["bright_ti5"])
                        if row["bright_ti5"] is not None
                        else None
                    ),

                    "frp": (
                        float(row["max_frp"])
                        if row["max_frp"] is not None
                        else None
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

                    # FIRMS confidence is categorical (l/n/h). It is kept
                    # separately from ThermoIntel's source-class confidence.
                    "detection_confidence": normalize_detection_confidence(row["confidence"]),
                    "detection_confidence_raw": row["confidence"],
                    "daynight": row["daynight"],
                    "version": row["version"],
                    "source": row["source"],
                    "detection_count": row["detection_count"],
                    "ml_anomaly_score": (
                        float(row["ml_anomaly_score"])
                        if row["ml_anomaly_score"] is not None else None
                    ),
                    "ml_normality_score": (
                        float(row["ml_normality_score"])
                        if row["ml_normality_score"] is not None else None
                    ),
                    "ml_model_name": row["ml_model_name"],
                    "ml_model_version": row["ml_model_version"],
                    "ml_predicted_class": row["ml_predicted_class"],
                    "ml_classification_confidence": (
                        float(row["ml_classification_confidence"])
                        if row["ml_classification_confidence"] is not None else None
                    ),
                    "ml_class_probabilities": row["ml_class_probabilities"] or {},
                    "ml_training_label_source": row["ml_training_label_source"],

                    "thermal_classification": (
                        row["classification"]
                        if row["classification"]
                        and str(row["classification"]).upper()
                            not in ("THERMAL ANOMALY", "OTHER THERMAL ANOMALY")
                        and str(row["classification"]).upper() != "OTHER THERMAL SOURCE"
                        else _classify_source(
                            {
                                "max_frp": row["max_frp"],
                                "max_bright_ti4": row["max_bright_ti4"],
                                "detection_count": row["detection_count"],
                                "observation_duration_minutes": row["observation_duration_minutes"],
                            },
                            {
                                "nearest_facility_id": row["nearest_facility_id"],
                                "nearest_facility_name": row["nearest_facility_name"],
                                "nearest_facility_type": row["nearest_facility_type"],
                                "nearest_industrial_type": row["nearest_industrial_type"],
                                "nearest_facility_distance_meters": row["nearest_facility_distance_meters"],
                                "is_inside_industrial_area": row["is_inside_industrial_area"],
                            },
                        )[0]
                    ),
                    "classification_confidence": (
                        float(row["classification_confidence"])
                        if row["classification_confidence"] is not None
                        and float(row["classification_confidence"]) > 0
                        else _classify_source(
                            {
                                "max_frp": row["max_frp"],
                                "max_bright_ti4": row["max_bright_ti4"],
                                "detection_count": row["detection_count"],
                                "observation_duration_minutes": row["observation_duration_minutes"],
                            },
                            {
                                "nearest_facility_id": row["nearest_facility_id"],
                                "nearest_facility_name": row["nearest_facility_name"],
                                "nearest_facility_type": row["nearest_facility_type"],
                                "nearest_industrial_type": row["nearest_industrial_type"],
                                "nearest_facility_distance_meters": row["nearest_facility_distance_meters"],
                                "is_inside_industrial_area": row["is_inside_industrial_area"],
                            },
                        )[1]
                    ),
                }
            )

        return {
            "count": len(events),
            "events": events,
            "window_hours": window_hours,
        }

    except Exception as exc:
        print("[Events] Database error:", repr(exc))

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve thermal events.",
        ) from exc


# ============================================================
# CURRENT EVENT SUMMARY
# ============================================================

@router.get("/summary")
def get_event_summary(
    window_hours: int = Query(default=24, ge=1),
):
    """
    Return statistics for the selected rolling event window.
    """

    query = text(
        """
        SELECT
            COUNT(*) AS total_events,
            AVG(max_frp) AS average_frp,
            MAX(max_frp) AS maximum_frp,
            MIN(first_detected_at) AS earliest_event,
            MAX(last_detected_at) AS latest_event

        FROM processed.thermal_events

        WHERE last_detected_at >= (
            CURRENT_TIMESTAMP - (:window_hours * INTERVAL '1 hour')
        )
        """
    )

    try:
        with engine.connect() as connection:
            row = connection.execute(query, {"window_hours": window_hours}).mappings().one()

        return {
            "total_events": int(row["total_events"] or 0),

            "average_frp": (
                float(row["average_frp"])
                if row["average_frp"] is not None
                else None
            ),

            "maximum_frp": (
                float(row["maximum_frp"])
                if row["maximum_frp"] is not None
                else None
            ),

            "earliest_event": (
                row["earliest_event"].isoformat()
                if row["earliest_event"]
                else None
            ),

            "latest_event": (
                row["latest_event"].isoformat()
                if row["latest_event"]
                else None
            ),

            "window_hours": window_hours,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate current event summary.",
        ) from exc


# ============================================================
# CURRENT NEARBY RAW DETECTIONS
# ============================================================

@router.get("/nearby")
def get_nearby_events(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=10, gt=0, le=500),
):
    """Return raw FIRMS observations near a coordinate."""

    query = text(
        """
        SELECT
            id,
            latitude,
            longitude,
            acquisition_datetime,
            satellite,
            instrument,
            bright_ti4,
            bright_ti5,
            frp,
            confidence,
            daynight,
            version,
            source,

            ST_Distance(
                geom::geography,
                ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude),
                    4326
                )::geography
            ) AS distance_meters

        FROM raw.firms_events

        WHERE acquisition_datetime >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )

        AND ST_DWithin(
            geom::geography,
            ST_SetSRID(
                ST_MakePoint(:longitude, :latitude),
                4326
            )::geography,
            :radius_meters
        )

        ORDER BY distance_meters ASC
        """
    )

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_meters": radius_km * 1000,
                },
            ).mappings().all()

        events = []

        for row in rows:
            events.append(
                {
                    "id": row["id"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),

                    "acquisition_datetime": (
                        row["acquisition_datetime"].isoformat()
                        if row["acquisition_datetime"]
                        else None
                    ),

                    "satellite": row["satellite"],
                    "instrument": row["instrument"],

                    "bright_ti4": (
                        float(row["bright_ti4"])
                        if row["bright_ti4"] is not None
                        else None
                    ),

                    "bright_ti5": (
                        float(row["bright_ti5"])
                        if row["bright_ti5"] is not None
                        else None
                    ),

                    "frp": (
                        float(row["frp"])
                        if row["frp"] is not None
                        else None
                    ),

                    "confidence": row["confidence"],
                    "daynight": row["daynight"],
                    "version": row["version"],
                    "source": row["source"],

                    "distance_meters": round(
                        float(row["distance_meters"]),
                        2,
                    ),
                }
            )

        return {
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km,
            "count": len(events),
            "events": events,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve nearby thermal detections.",
        ) from exc


# ============================================================
# PROCESSED EVENT + INDUSTRIAL CONTEXT
# ============================================================

@router.get("/{event_id}/context")
def get_event_context(event_id: int):
    """Return event details, nearby OSM facilities and risk intelligence.

    This endpoint intentionally computes the geospatial facility context directly
    from PostGIS instead of depending on a precomputed context row. That keeps
    the Event View usable immediately after OSM ingestion and avoids the 500
    errors caused by stale/missing derived-context records.
    """
    event_query = text("""
        SELECT
            e.id,
            e.centroid_latitude AS latitude,
            e.centroid_longitude AS longitude,
            e.first_detected_at,
            e.last_detected_at,
            e.detection_count,
            e.observation_duration_minutes,
            e.max_frp,
            e.average_frp,
            e.max_bright_ti4,
            e.average_bright_ti4,
            e.satellites,
            rep.satellite,
            rep.instrument,
            rep.bright_ti5,
            rep.confidence,
            rep.daynight,
            rep.version,
            rep.source
        FROM processed.thermal_events e
        LEFT JOIN LATERAL (
            SELECT f.satellite, f.instrument, f.bright_ti5, f.confidence,
                   f.daynight, f.version, f.source
            FROM processed.thermal_event_detections m
            JOIN raw.firms_events f ON f.id = m.firms_event_id
            WHERE m.event_id = e.id
            ORDER BY f.frp DESC NULLS LAST, f.acquisition_datetime DESC
            LIMIT 1
        ) rep ON TRUE
        WHERE e.id = :event_id
    """)

    facility_query = text("""
        SELECT
            f.id,
            f.osm_type,
            f.osm_id,
            f.name,
            f.facility_type,
            f.industrial_type,
            f.latitude,
            f.longitude,
            f.source,
            ST_Distance(
                f.geom::geography,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
            ) AS distance_meters,
            CASE
                WHEN ST_GeometryType(f.geom) IN ('ST_Polygon', 'ST_MultiPolygon')
                THEN ST_Covers(
                    f.geom,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                )
                ELSE FALSE
            END AS contains_event
        FROM raw.industrial_facilities f
        WHERE ST_DWithin(
            f.geom::geography,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
            :radius_meters
        )
        ORDER BY distance_meters ASC, f.id ASC
        LIMIT :limit
    """)

    risk_query = text("""
        SELECT r.risk_score, r.risk_band, r.severity, r.confidence_score,
               r.thermal_score, r.persistence_score, r.industrial_score,
               r.evidence_score, r.industrial_context, r.intelligence_reason,
               ml.anomaly_score AS ml_anomaly_score,
               ml.normality_score AS ml_normality_score,
               ml.model_name AS ml_model_name,
               ml.model_version AS ml_model_version,
               ml.predicted_class AS ml_predicted_class,
               ml.classification_confidence AS ml_classification_confidence,
               ml.class_probabilities AS ml_class_probabilities,
               ml.training_label_source AS ml_training_label_source
        FROM processed.event_risk_scores r
        LEFT JOIN processed.event_ml_scores ml
            ON ml.event_id = r.event_id
        WHERE r.event_id = :event_id
    """)

    try:
        with engine.connect() as connection:
            event_row = connection.execute(
                event_query, {"event_id": event_id}
            ).mappings().one_or_none()

            if event_row is None:
                raise HTTPException(status_code=404, detail="Thermal event not found.")

            base_params = {
                "latitude": float(event_row["latitude"]),
                "longitude": float(event_row["longitude"]),
                "radius_meters": 10000,
                "limit": 50,
            }
            facility_rows = connection.execute(
                facility_query, base_params
            ).mappings().all()

            try:
                risk_row = connection.execute(
                    risk_query, {"event_id": event_id}
                ).mappings().one_or_none()
            except Exception as risk_exc:
                print("[Events] Risk data unavailable:", repr(risk_exc))
                risk_row = None

        nearby_facilities = []
        for row in facility_rows:
            nearby_facilities.append({
                "id": row["id"],
                "osm_type": row["osm_type"],
                "osm_id": row["osm_id"],
                "name": row["name"],
                "facility_type": row["facility_type"],
                "industrial_type": row["industrial_type"],
                "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
                "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
                "source": row["source"],
                "distance_meters": float(row["distance_meters"]) if row["distance_meters"] is not None else None,
                "contains_event": bool(row["contains_event"]),
            })

        nearest = nearby_facilities[0] if nearby_facilities else None
        within_1km = sum(
            1 for f in nearby_facilities
            if f["distance_meters"] is not None and f["distance_meters"] <= 1000
        )
        within_5km = sum(
            1 for f in nearby_facilities
            if f["distance_meters"] is not None and f["distance_meters"] <= 5000
        )
        inside_industrial_area = bool(
            any(f.get("contains_event") for f in nearby_facilities)
            or (
                nearest
                and nearest["distance_meters"] is not None
                and nearest["distance_meters"] <= 250
            )
        )

        intelligence_row = None
        with engine.connect() as connection:
            intelligence_row = (
                connection.execute(
                    text("""
                        SELECT classification, classification_confidence, confidence_score,
                               class_probabilities, intelligence_reason,
                               thermal_score, persistence_score, industrial_score, updated_at
                        FROM processed.event_intelligence
                        WHERE event_id = :event_id
                    """),
                    {"event_id": event_id},
                )
                .mappings()
                .first()
            )

        # Event details must never remain stuck on a stale/generic processing
        # message. Recompute this one event from the current contextual data and
        # current XGBoost score, then persist the result. This is intentionally
        # scoped to the clicked event so the detail page remains responsive.
        try:
            computed = classify_event(event_id)
            if computed:
                save_event_intelligence(computed)
                process_event_risk(event_id)
                with engine.connect() as connection:
                    intelligence_row = (
                        connection.execute(
                            text("""
                                SELECT classification, classification_confidence, confidence_score,
                                       class_probabilities, intelligence_reason,
                                       thermal_score, persistence_score, industrial_score, updated_at
                                FROM processed.event_intelligence
                                WHERE event_id = :event_id
                            """),
                            {"event_id": event_id},
                        )
                        .mappings()
                        .first()
                    )
                    risk_row = connection.execute(
                        risk_query, {"event_id": event_id}
                    ).mappings().one_or_none()
        except Exception as intelligence_exc:
            print("[Events] Could not refresh intelligence:", repr(intelligence_exc))

        ml_score = None
        if risk_row:
            ml_score = {
                "anomaly_score": float(risk_row["ml_anomaly_score"]) if risk_row["ml_anomaly_score"] is not None else None,
                "normality_score": float(risk_row["ml_normality_score"]) if risk_row["ml_normality_score"] is not None else None,
                "model_name": risk_row["ml_model_name"],
                "model_version": risk_row["ml_model_version"],
                "predicted_class": risk_row["ml_predicted_class"],
                "classification_confidence": (
                    float(risk_row["ml_classification_confidence"])
                    if risk_row["ml_classification_confidence"] is not None else None
                ),
                "class_probabilities": risk_row["ml_class_probabilities"] or {},
                "training_label_source": risk_row["ml_training_label_source"],
            }

        thermal_event = {
            "id": event_row["id"],
            "latitude": float(event_row["latitude"]) if event_row["latitude"] is not None else None,
            "longitude": float(event_row["longitude"]) if event_row["longitude"] is not None else None,
            "acquisition_datetime": event_row["last_detected_at"].isoformat() if event_row["last_detected_at"] else None,
            "first_detected_at": event_row["first_detected_at"].isoformat() if event_row["first_detected_at"] else None,
            "last_detected_at": event_row["last_detected_at"].isoformat() if event_row["last_detected_at"] else None,
            "satellite": event_row["satellite"],
            "satellites": event_row["satellites"],
            "instrument": event_row["instrument"],
            "bright_ti4": float(event_row["max_bright_ti4"]) if event_row["max_bright_ti4"] is not None else None,
            "bright_ti5": float(event_row["bright_ti5"]) if event_row["bright_ti5"] is not None else None,
            "frp": float(event_row["max_frp"]) if event_row["max_frp"] is not None else None,
            "average_frp": float(event_row["average_frp"]) if event_row["average_frp"] is not None else None,
            "detection_confidence": normalize_detection_confidence(event_row["confidence"]),
            "detection_confidence_raw": event_row["confidence"],
            "daynight": event_row["daynight"],
            "version": event_row["version"],
            "source": event_row["source"],
            "detection_count": event_row["detection_count"],
            "ml_anomaly": ml_score,
            "thermal_classification": (
                intelligence_row["classification"]
                if intelligence_row
                and intelligence_row["classification"]
                and str(intelligence_row["classification"]).upper()
                    not in ("THERMAL ANOMALY", "OTHER THERMAL ANOMALY")
                and str(intelligence_row["classification"]).upper() != "OTHER THERMAL SOURCE"
                else _classify_source(
                    {
                        "max_frp": event_row["max_frp"],
                        "max_bright_ti4": event_row["max_bright_ti4"],
                        "detection_count": event_row["detection_count"],
                        "observation_duration_minutes": event_row["observation_duration_minutes"],
                    },
                    {
                        "nearest_facility_id": nearest["id"] if nearest else None,
                        "nearest_facility_name": nearest["name"] if nearest else None,
                        "nearest_facility_type": nearest["facility_type"] if nearest else None,
                        "nearest_industrial_type": nearest["industrial_type"] if nearest else None,
                        "nearest_facility_distance_meters": nearest["distance_meters"] if nearest else None,
                        "is_inside_industrial_area": inside_industrial_area,
                    },
                )[0]
            ),
            "classification_confidence": (
                float(intelligence_row["classification_confidence"])
                if intelligence_row
                and intelligence_row["classification_confidence"] is not None
                and float(intelligence_row["classification_confidence"]) > 0
                else _classify_source(
                    {
                        "max_frp": event_row["max_frp"],
                        "max_bright_ti4": event_row["max_bright_ti4"],
                        "detection_count": event_row["detection_count"],
                        "observation_duration_minutes": event_row["observation_duration_minutes"],
                    },
                    {
                        "nearest_facility_id": nearest["id"] if nearest else None,
                        "nearest_facility_name": nearest["name"] if nearest else None,
                        "nearest_facility_type": nearest["facility_type"] if nearest else None,
                        "nearest_industrial_type": nearest["industrial_type"] if nearest else None,
                        "nearest_facility_distance_meters": nearest["distance_meters"] if nearest else None,
                        "is_inside_industrial_area": inside_industrial_area,
                    },
                )[1]
            ),
            "probable_cause": (intelligence_row["classification"] if intelligence_row else None),
            "probable_cause_reason": (
                intelligence_row["intelligence_reason"]
                if intelligence_row and intelligence_row["intelligence_reason"]
                else (
                    f"Probable source: {intelligence_row["classification"]} "
                    f"({float(intelligence_row["classification_confidence"] or 0) * 100:.1f}% evidence confidence). "
                    f"Evidence — thermal {float(intelligence_row["thermal_score"] or 0):.2f}, "
                    f"persistence {float(intelligence_row["persistence_score"] or 0):.2f}, "
                    f"industrial {float(intelligence_row["industrial_score"] or 0):.2f}."
                ) if intelligence_row else None
            ),
            "cause_evidence": (intelligence_row["class_probabilities"] if intelligence_row else {}),
            "thermal_score": float(intelligence_row["thermal_score"]) if intelligence_row and intelligence_row["thermal_score"] is not None else None,
            "persistence_score": float(intelligence_row["persistence_score"]) if intelligence_row and intelligence_row["persistence_score"] is not None else None,
            "industrial_score": float(intelligence_row["industrial_score"]) if intelligence_row and intelligence_row["industrial_score"] is not None else None,
        }

        nearest_facility = None
        if nearest:
            nearest_facility = {
                **nearest,
                "facilities_within_1km": within_1km,
                "facilities_within_5km": within_5km,
                "is_inside_industrial_area": inside_industrial_area,
            }

        risk = None
        if risk_row:
            risk = {
                "risk_score": float(risk_row["risk_score"] or 0),
                "risk_band": risk_row["risk_band"],
                "severity": risk_row["severity"],
                "confidence_score": float(risk_row["confidence_score"] or 0),
                "thermal_score": float(risk_row["thermal_score"] or 0),
                "persistence_score": float(risk_row["persistence_score"] or 0),
                "industrial_score": float(risk_row["industrial_score"] or 0),
                "evidence_score": float(risk_row["evidence_score"] or 0),
                "industrial_context": risk_row["industrial_context"],
                "intelligence_reason": risk_row["intelligence_reason"],
                "ml_anomaly_score": float(risk_row["ml_anomaly_score"]) if risk_row["ml_anomaly_score"] is not None else None,
                "ml_normality_score": float(risk_row["ml_normality_score"]) if risk_row["ml_normality_score"] is not None else None,
                "ml_model_name": risk_row["ml_model_name"],
                "ml_model_version": risk_row["ml_model_version"],
                "ml_predicted_class": risk_row["ml_predicted_class"],
                "ml_classification_confidence": (
                    float(risk_row["ml_classification_confidence"])
                    if risk_row["ml_classification_confidence"] is not None else None
                ),
                "ml_class_probabilities": risk_row["ml_class_probabilities"] or {},
                "ml_training_label_source": risk_row["ml_training_label_source"],
            }

        return {
            "thermal_event": thermal_event,
            "nearest_facility": nearest_facility,
            "nearby_facilities": nearby_facilities,
            "facility_summary": {
                "within_1km": within_1km,
                "within_5km": within_5km,
                "within_10km": len(nearby_facilities),
            },
            "risk": risk,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("[Events] Context error:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event context. Check PostGIS and the event ID.",
        ) from exc


# ============================================================
# SINGLE PROCESSED THERMAL EVENT
# ============================================================

@router.get("/{event_id}")
def get_event_by_id(event_id: int):

    query = text(
        """
        SELECT
            e.id,
            e.centroid_latitude AS latitude,
            e.centroid_longitude AS longitude,
            e.first_detected_at,
            e.last_detected_at,
            e.detection_count,
            e.observation_duration_minutes,
            e.max_frp,
            e.average_frp,
            e.max_bright_ti4,
            e.average_bright_ti4,
            e.satellites

        FROM processed.thermal_events e

        WHERE e.id = :event_id
        """
    )

    try:
        with engine.connect() as connection:
            row = connection.execute(
                query,
                {"event_id": event_id},
            ).mappings().one_or_none()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Thermal event not found.",
            )

        return {
            "id": row["id"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],

            "acquisition_datetime": (
                row["last_detected_at"].isoformat()
                if row["last_detected_at"]
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

            "frp": (
                float(row["max_frp"])
                if row["max_frp"] is not None
                else None
            ),

            "average_frp": (
                float(row["average_frp"])
                if row["average_frp"] is not None
                else None
            ),

            "bright_ti4": (
                float(row["max_bright_ti4"])
                if row["max_bright_ti4"] is not None
                else None
            ),

            "average_bright_ti4": (
                float(row["average_bright_ti4"])
                if row["average_bright_ti4"] is not None
                else None
            ),

            "satellites": row["satellites"],
            "detection_count": row["detection_count"],
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve thermal event.",
        ) from exc