from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.database import engine


router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["Event Intelligence"],
)


# ============================================================
# INTELLIGENCE SUMMARY
# ============================================================

@router.get("/summary")
def get_intelligence_summary():
    """
    Return overall ThermoIntel intelligence and risk statistics.
    """

    overview_query = text(
        """
        SELECT
            COUNT(*) AS total_events,
            AVG(risk_score) AS average_risk_score,
            MAX(risk_score) AS maximum_risk_score
        FROM processed.event_risk_scores r
        JOIN processed.thermal_events e
            ON e.id = r.event_id
        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        """
    )

    distribution_query = text(
        """
        SELECT
            risk_band,
            COUNT(*) AS event_count
        FROM processed.event_risk_scores r
        JOIN processed.thermal_events e
            ON e.id = r.event_id
        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        GROUP BY risk_band
        """
    )

    thermal_query = text(
        """
        SELECT
            COUNT(*) AS total_events,
            AVG(max_frp) AS average_max_frp,
            MAX(max_frp) AS maximum_frp,
            AVG(detection_count) AS average_detection_count,
            MIN(first_detected_at) AS earliest_event,
            MAX(last_detected_at) AS latest_event
        FROM processed.thermal_events
        WHERE last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        """
    )

    industrial_query = text(
        """
        SELECT
            COUNT(*) AS total_context_records,

            COUNT(
                CASE
                    WHEN nearest_facility_id IS NOT NULL
                    THEN 1
                END
            ) AS events_with_industrial_facility,

            COUNT(
                CASE
                    WHEN nearest_facility_distance_meters <= 1000
                    THEN 1
                END
            ) AS events_within_1km,

            COUNT(
                CASE
                    WHEN nearest_facility_distance_meters <= 5000
                    THEN 1
                END
            ) AS events_within_5km,

            COUNT(
                CASE
                    WHEN is_inside_industrial_area = TRUE
                    THEN 1
                END
            ) AS events_inside_industrial_area

        FROM processed.event_industrial_context c
        JOIN processed.thermal_events e
            ON e.id = c.event_id
        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        """
    )

    try:
        with engine.connect() as connection:

            overview = (
                connection.execute(
                    overview_query
                )
                .mappings()
                .one()
            )

            distribution_rows = (
                connection.execute(
                    distribution_query
                )
                .mappings()
                .all()
            )

            thermal = (
                connection.execute(
                    thermal_query
                )
                .mappings()
                .one()
            )

            industrial = (
                connection.execute(
                    industrial_query
                )
                .mappings()
                .one()
            )

        risk_distribution = {
            "critical": 0,
            "high": 0,
            "moderate": 0,
            "low": 0,
        }

        for row in distribution_rows:
            band = row["risk_band"]

            if band:
                risk_distribution[
                    band.lower()
                ] = int(row["event_count"])

        return {
            "overview": {
                "total_events": int(
                    overview["total_events"] or 0
                ),
                "average_risk_score": (
                    float(
                        overview["average_risk_score"]
                    )
                    if overview["average_risk_score"]
                    is not None
                    else None
                ),
                "maximum_risk_score": (
                    float(
                        overview["maximum_risk_score"]
                    )
                    if overview["maximum_risk_score"]
                    is not None
                    else None
                ),
            },

            "risk_distribution":
                risk_distribution,

            "thermal": {
                "total_events": int(
                    thermal["total_events"] or 0
                ),
                "average_max_frp": (
                    float(
                        thermal["average_max_frp"]
                    )
                    if thermal["average_max_frp"]
                    is not None
                    else None
                ),
                "maximum_frp": (
                    float(
                        thermal["maximum_frp"]
                    )
                    if thermal["maximum_frp"]
                    is not None
                    else None
                ),
                "average_detection_count": (
                    float(
                        thermal[
                            "average_detection_count"
                        ]
                    )
                    if thermal[
                        "average_detection_count"
                    ] is not None
                    else None
                ),
                "earliest_event": (
                    thermal[
                        "earliest_event"
                    ].isoformat()
                    if thermal[
                        "earliest_event"
                    ]
                    else None
                ),
                "latest_event": (
                    thermal[
                        "latest_event"
                    ].isoformat()
                    if thermal[
                        "latest_event"
                    ]
                    else None
                ),
            },

            "industrial_context": {
                "total_context_records": int(
                    industrial[
                        "total_context_records"
                    ] or 0
                ),
                "events_with_industrial_facility": int(
                    industrial[
                        "events_with_industrial_facility"
                    ] or 0
                ),
                "events_within_1km": int(
                    industrial[
                        "events_within_1km"
                    ] or 0
                ),
                "events_within_5km": int(
                    industrial[
                        "events_within_5km"
                    ] or 0
                ),
                "events_inside_industrial_area": int(
                    industrial[
                        "events_inside_industrial_area"
                    ] or 0
                ),
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate intelligence summary.",
        ) from exc


# ============================================================
# INTELLIGENCE EVENTS
# ============================================================

@router.get("/events")
def get_intelligence_events(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):
    """
    Return event intelligence and risk records.
    """

    query = text(
        """
        SELECT
            r.event_id,

            r.risk_score,
            r.risk_band,

            r.severity,
            r.confidence_score,

            r.thermal_score,
            r.persistence_score,
            r.industrial_score,

            r.evidence_score,

            r.industrial_context,
            r.intelligence_reason,

            e.centroid_latitude AS latitude,
            e.centroid_longitude AS longitude,

            e.max_frp,
            e.average_frp,

            e.detection_count,

            e.first_detected_at,
            e.last_detected_at

        FROM processed.event_risk_scores r

        JOIN processed.thermal_events e
            ON e.id = r.event_id

        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )

        ORDER BY
            r.risk_score DESC,
            e.last_detected_at DESC

        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:

            rows = (
                connection.execute(
                    query,
                    {"limit": limit},
                )
                .mappings()
                .all()
            )

        events = []

        for row in rows:

            events.append(
                {
                    "event_id":
                        row["event_id"],

                    "risk_score":
                        float(row["risk_score"]),

                    "risk_band":
                        row["risk_band"],

                    "severity":
                        row["severity"],

                    "confidence_score":
                        float(
                            row["confidence_score"]
                        ),

                    "thermal_score":
                        float(
                            row["thermal_score"]
                        ),

                    "persistence_score":
                        float(
                            row["persistence_score"]
                        ),

                    "industrial_score":
                        float(
                            row["industrial_score"]
                        ),

                    "evidence_score":
                        float(
                            row["evidence_score"]
                        ),

                    "industrial_context":
                        row["industrial_context"],

                    "intelligence_reason":
                        row["intelligence_reason"],

                    "latitude":
                        float(row["latitude"]),

                    "longitude":
                        float(row["longitude"]),

                    "max_frp":
                        float(row["max_frp"])
                        if row["max_frp"] is not None
                        else None,

                    "average_frp":
                        float(row["average_frp"])
                        if row["average_frp"] is not None
                        else None,

                    "detection_count":
                        row["detection_count"],

                    "first_detected_at":
                        (
                            row["first_detected_at"]
                            .isoformat()
                            if row["first_detected_at"]
                            else None
                        ),

                    "last_detected_at":
                        (
                            row["last_detected_at"]
                            .isoformat()
                            if row["last_detected_at"]
                            else None
                        ),
                }
            )

        return {
            "count": len(events),
            "events": events,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event intelligence.",
        ) from exc


# ============================================================
# HIGH-RISK EVENTS
# ============================================================

@router.get("/high-risk")
def get_high_risk_events(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    """
    Return the highest-risk thermal events.
    """

    query = text(
        """
        SELECT
            r.event_id,
            r.risk_score,
            r.risk_band,
            r.severity,
            r.confidence_score,
            r.industrial_context,
            r.intelligence_reason,

            e.centroid_latitude AS latitude,
            e.centroid_longitude AS longitude,
            e.max_frp,
            e.detection_count,
            e.first_detected_at,
            e.last_detected_at

        FROM processed.event_risk_scores r

        JOIN processed.thermal_events e
            ON e.id = r.event_id

        WHERE r.risk_band IN (
            'CRITICAL',
            'HIGH'
        )

        AND e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )

        ORDER BY
            r.risk_score DESC

        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:

            rows = (
                connection.execute(
                    query,
                    {"limit": limit},
                )
                .mappings()
                .all()
            )

        events = []

        for row in rows:

            events.append(
                {
                    "event_id":
                        row["event_id"],

                    "risk_score":
                        float(row["risk_score"]),

                    "risk_band":
                        row["risk_band"],

                    "severity":
                        row["severity"],

                    "confidence_score":
                        float(
                            row["confidence_score"]
                        ),

                    "industrial_context":
                        row["industrial_context"],

                    "intelligence_reason":
                        row["intelligence_reason"],

                    "latitude":
                        float(row["latitude"]),

                    "longitude":
                        float(row["longitude"]),

                    "max_frp":
                        float(row["max_frp"])
                        if row["max_frp"] is not None
                        else None,

                    "detection_count":
                        row["detection_count"],

                    "first_detected_at":
                        (
                            row["first_detected_at"]
                            .isoformat()
                            if row["first_detected_at"]
                            else None
                        ),

                    "last_detected_at":
                        (
                            row["last_detected_at"]
                            .isoformat()
                            if row["last_detected_at"]
                            else None
                        ),
                }
            )

        return {
            "count": len(events),
            "events": events,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve high-risk events.",
        ) from exc


# ============================================================
# SINGLE EVENT INTELLIGENCE
# ============================================================

@router.get("/events/{event_id}")
def get_event_intelligence(
    event_id: int,
):
    """
    Return complete intelligence information for one event.
    """

    query = text(
        """
        SELECT
            r.event_id,

            r.risk_score,
            r.risk_band,

            r.severity,
            r.confidence_score,

            r.thermal_score,
            r.persistence_score,
            r.industrial_score,

            r.evidence_score,

            r.industrial_context,
            r.intelligence_reason,

            e.centroid_latitude AS latitude,
            e.centroid_longitude AS longitude,

            e.first_detected_at,
            e.last_detected_at,

            e.observation_duration_minutes,
            e.detection_count,

            e.max_frp,
            e.average_frp,

            e.max_bright_ti4,
            e.average_bright_ti4,

            e.satellites

        FROM processed.event_risk_scores r

        JOIN processed.thermal_events e
            ON e.id = r.event_id

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
                detail="Event intelligence not found.",
            )

        return {
            "event_id":
                row["event_id"],

            "risk": {
                "risk_score":
                    float(row["risk_score"]),

                "risk_band":
                    row["risk_band"],

                "severity":
                    row["severity"],

                "confidence_score":
                    float(
                        row["confidence_score"]
                    ),
            },

            "evidence": {
                "thermal_score":
                    float(
                        row["thermal_score"]
                    ),

                "persistence_score":
                    float(
                        row["persistence_score"]
                    ),

                "industrial_score":
                    float(
                        row["industrial_score"]
                    ),

                "evidence_score":
                    float(
                        row["evidence_score"]
                    ),
            },

            "industrial": {
                "context":
                    row["industrial_context"],
            },

            "thermal": {
                "latitude":
                    float(row["latitude"]),

                "longitude":
                    float(row["longitude"]),

                "max_frp":
                    float(row["max_frp"])
                    if row["max_frp"] is not None
                    else None,

                "average_frp":
                    float(row["average_frp"])
                    if row["average_frp"] is not None
                    else None,

                "max_bright_ti4":
                    float(
                        row["max_bright_ti4"]
                    )
                    if row["max_bright_ti4"]
                    is not None
                    else None,

                "average_bright_ti4":
                    float(
                        row["average_bright_ti4"]
                    )
                    if row["average_bright_ti4"]
                    is not None
                    else None,

                "detection_count":
                    row["detection_count"],

                "observation_duration_minutes":
                    float(
                        row[
                            "observation_duration_minutes"
                        ]
                    )
                    if row[
                        "observation_duration_minutes"
                    ] is not None
                    else None,

                "satellites":
                    row["satellites"],
            },

            "time": {
                "first_detected_at":
                    (
                        row["first_detected_at"]
                        .isoformat()
                        if row["first_detected_at"]
                        else None
                    ),

                "last_detected_at":
                    (
                        row["last_detected_at"]
                        .isoformat()
                        if row["last_detected_at"]
                        else None
                    ),
            },

            "intelligence_reason":
                row["intelligence_reason"],
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event intelligence.",
        ) from exc