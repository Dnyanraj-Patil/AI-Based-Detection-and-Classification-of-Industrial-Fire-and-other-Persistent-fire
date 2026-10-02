from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.database import engine


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
def get_dashboard_summary(
    window_hours: Optional[int] = Query(
        default=None,
        ge=1,
        description="Optional rolling window in hours. Omit for all available data.",
    ),
    start: Optional[datetime] = Query(
        default=None,
        description="Optional custom start timestamp.",
    ),
    end: Optional[datetime] = Query(default=None, description="Optional custom end timestamp."),
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    radius_km: Optional[float] = Query(default=None, gt=0, le=500),
):
    """
    Return one canonical dashboard snapshot.

    Default:
        All available processed thermal events.

    Optional:
        window_hours=24   -> last 24 hours
        window_hours=72   -> last 3 days
        window_hours=168  -> last 7 days
    Custom:
        start=<ISO timestamp>&end=<ISO timestamp>

    Every dashboard statistic uses the same selected event window.
    """

    try:
        # --------------------------------------------------
        # Validate mutually exclusive window parameters
        # --------------------------------------------------

        if window_hours is not None and (start is not None or end is not None):
            raise HTTPException(
                status_code=400,
                detail="Use either window_hours or start/end, not both.",
            )

        if (start is None) != (end is None):
            raise HTTPException(
                status_code=400,
                detail="Both start and end must be provided for a custom range.",
            )

        if start is not None and end is not None and start > end:
            raise HTTPException(
                status_code=400,
                detail="start must be earlier than end.",
            )

        # --------------------------------------------------
        # Build ONE canonical event filter.
        #
        # Every query below uses this same condition.
        # --------------------------------------------------

        if (latitude is None) != (longitude is None):
            raise HTTPException(status_code=400, detail="latitude and longitude must be provided together.")
        if (latitude is not None or longitude is not None) and radius_km is None:
            radius_km = 25.0

        conditions = []
        params = {}

        if window_hours is not None:
            conditions.append(
                "e.last_detected_at >= "
                "(CURRENT_TIMESTAMP - (:window_hours * INTERVAL '1 hour'))"
            )
            params["window_hours"] = window_hours

        elif start is not None and end is not None:
            conditions.append("e.last_detected_at >= :start_timestamp")
            conditions.append("e.last_detected_at <= :end_timestamp")
            params["start_timestamp"] = start
            params["end_timestamp"] = end

        if latitude is not None:
            conditions.append("ST_DWithin(e.geom::geography, ST_SetSRID(ST_MakePoint(:longitude, :latitude),4326)::geography,:radius_meters)")
            params.update({"latitude": latitude, "longitude": longitude, "radius_meters": radius_km * 1000})

        # No condition means ALL DATA.
        event_filter = ""

        if conditions:
            event_filter = "WHERE " + " AND ".join(conditions)

        # --------------------------------------------------
        # DATABASE
        # --------------------------------------------------

        with engine.connect() as connection:

            # ==================================================
            # THERMAL EVENTS
            # ==================================================

            thermal = connection.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) AS total_events,
                        AVG(e.max_frp) AS average_frp,
                        MAX(e.max_frp) AS maximum_frp,
                        MIN(e.first_detected_at) AS earliest_event,
                        MAX(e.last_detected_at) AS latest_event,
                        AVG(e.detection_count) AS average_detection_count,
                        COUNT(*) FILTER (WHERE UPPER(COALESCE(rep.daynight,'')) = 'D') AS day_events,
                        COUNT(*) FILTER (WHERE UPPER(COALESCE(rep.daynight,'')) = 'N') AS night_events
                    FROM processed.thermal_events e
                    LEFT JOIN LATERAL (
                        SELECT f.daynight
                        FROM processed.thermal_event_detections m
                        JOIN raw.firms_events f ON f.id = m.firms_event_id
                        WHERE m.event_id = e.id
                        ORDER BY f.frp DESC NULLS LAST, f.acquisition_datetime DESC
                        LIMIT 1
                    ) rep ON TRUE
                    {event_filter}
                    """
                ),
                params,
            ).mappings().one()

            # ==================================================
            # RISK
            # ==================================================

            risk_conditions = []

            if window_hours is not None:
                risk_conditions.append(
                    "e.last_detected_at >= "
                    "(CURRENT_TIMESTAMP - (:window_hours * INTERVAL '1 hour'))"
                )

            elif start is not None and end is not None:
                risk_conditions.append("e.last_detected_at >= :start_timestamp")
                risk_conditions.append("e.last_detected_at <= :end_timestamp")

            if latitude is not None:
                risk_conditions.append("ST_DWithin(e.geom::geography, ST_SetSRID(ST_MakePoint(:longitude, :latitude),4326)::geography,:radius_meters)")

            risk_filter = ""

            if risk_conditions:
                risk_filter = "WHERE " + " AND ".join(risk_conditions)

            risk = connection.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) AS total_events,
                        AVG(r.risk_score) AS average_risk_score,
                        MAX(r.risk_score) AS maximum_risk_score,

                        COUNT(*) FILTER (
                            WHERE r.risk_band = 'CRITICAL'
                        ) AS critical_events,

                        COUNT(*) FILTER (
                            WHERE r.risk_band = 'HIGH'
                        ) AS high_events,

                        COUNT(*) FILTER (
                            WHERE r.risk_band = 'MODERATE'
                        ) AS moderate_events,

                        COUNT(*) FILTER (
                            WHERE r.risk_band = 'LOW'
                        ) AS low_events

                    FROM processed.event_risk_scores r

                    JOIN processed.thermal_events e
                        ON e.id = r.event_id

                    {risk_filter}
                    """
                ),
                params,
            ).mappings().one()

            # ==================================================
            # INDUSTRIAL CONTEXT
            # ==================================================

            industrial = connection.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) AS total_context_records,

                        COUNT(*) FILTER (
                            WHERE c.nearest_facility_id IS NOT NULL
                        ) AS events_with_industrial_facility,

                        COUNT(*) FILTER (
                            WHERE c.facilities_within_1km > 0
                        ) AS events_within_1km,

                        COUNT(*) FILTER (
                            WHERE c.facilities_within_5km > 0
                        ) AS events_within_5km,

                        COUNT(*) FILTER (
                            WHERE c.is_inside_industrial_area = TRUE
                        ) AS events_inside_industrial_area

                    FROM processed.event_industrial_context c

                    JOIN processed.thermal_events e
                        ON e.id = c.event_id

                    {event_filter}
                    """
                ),
                params,
            ).mappings().one()

            # ==================================================
            # TOP RISK EVENTS
            # ==================================================

            top_events = connection.execute(
                text(
                    f"""
                    SELECT
                        r.event_id,
                        r.risk_score,
                        r.risk_band,
                        r.severity,
                        r.confidence_score,
                        r.industrial_context,

                        e.centroid_latitude AS latitude,
                        e.centroid_longitude AS longitude,

                        e.max_frp,
                        e.detection_count,
                        e.first_detected_at,
                        e.last_detected_at

                    FROM processed.event_risk_scores r

                    JOIN processed.thermal_events e
                        ON e.id = r.event_id

                    {risk_filter}

                    ORDER BY
                        r.risk_score DESC,
                        e.last_detected_at DESC

                    LIMIT 10
                    """
                ),
                params,
            ).mappings().all()

        # --------------------------------------------------
        # Formatting helpers
        # --------------------------------------------------

        def number(value):
            return float(value) if value is not None else None

        def iso(value):
            return value.isoformat() if value else None

        formatted_top_events = [
            {
                "event_id": row["event_id"],
                "risk_score": number(row["risk_score"]),
                "risk_band": row["risk_band"],
                "severity": row["severity"],
                "confidence_score": number(row["confidence_score"]),
                "industrial_context": row["industrial_context"],
                "latitude": number(row["latitude"]),
                "longitude": number(row["longitude"]),
                "max_frp": number(row["max_frp"]),
                "detection_count": row["detection_count"],
                "first_detected_at": iso(
                    row["first_detected_at"]
                ),
                "last_detected_at": iso(
                    row["last_detected_at"]
                ),
            }
            for row in top_events
        ]

        # --------------------------------------------------
        # Determine response window
        # --------------------------------------------------

        if window_hours is not None:
            window_type = "rolling"
            response_window_hours = window_hours

        elif start is not None and end is not None:
            window_type = "custom"
            response_window_hours = None

        else:
            window_type = "all"
            response_window_hours = None

        # --------------------------------------------------
        # CANONICAL RESPONSE
        # --------------------------------------------------

        return {
            "window": {
                "type": window_type,
                "window_hours": response_window_hours,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                "location": {
                    "label": None,
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_km": radius_km,
                } if latitude is not None else None,
            },

            "overview": {
                "total_events": int(
                    thermal["total_events"] or 0
                ),

                "average_risk_score": number(
                    risk["average_risk_score"]
                ),

                "maximum_risk_score": number(
                    risk["maximum_risk_score"]
                ),

                "risk_assessed_events": int(
                    risk["total_events"] or 0
                ),
            },

            "risk_distribution": {
                "critical": int(
                    risk["critical_events"] or 0
                ),

                "high": int(
                    risk["high_events"] or 0
                ),

                "moderate": int(
                    risk["moderate_events"] or 0
                ),

                "low": int(
                    risk["low_events"] or 0
                ),
            },

            "thermal": {
                "total_events": int(
                    thermal["total_events"] or 0
                ),

                "average_max_frp": number(
                    thermal["average_frp"]
                ),

                "maximum_frp": number(
                    thermal["maximum_frp"]
                ),

                "average_detection_count": number(thermal["average_detection_count"]),
                "day_events": int(thermal["day_events"] or 0),
                "night_events": int(thermal["night_events"] or 0),

                "earliest_event": iso(
                    thermal["earliest_event"]
                ),

                "latest_event": iso(
                    thermal["latest_event"]
                ),
            },

            "industrial_context": {
                "total_context_records": int(
                    industrial["total_context_records"] or 0
                ),

                "events_with_industrial_facility": int(
                    industrial["events_with_industrial_facility"] or 0
                ),

                "events_within_1km": int(
                    industrial["events_within_1km"] or 0
                ),

                "events_within_5km": int(
                    industrial["events_within_5km"] or 0
                ),

                "events_inside_industrial_area": int(
                    industrial["events_inside_industrial_area"] or 0
                ),
            },

            "top_risk_events": formatted_top_events,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "[Dashboard] Database error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate dashboard summary.",
        ) from exc