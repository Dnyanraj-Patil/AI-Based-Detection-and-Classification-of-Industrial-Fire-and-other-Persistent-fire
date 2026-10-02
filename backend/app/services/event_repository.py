from sqlalchemy import text

from app.db.database import engine


# ============================================================
# INSERT / UPDATE THERMAL EVENT
# ============================================================

UPSERT_EVENT_SQL = text(
    """
    INSERT INTO processed.thermal_events (

        first_detected_at,
        last_detected_at,

        observation_duration_minutes,

        detection_count,

        max_frp,
        average_frp,

        max_bright_ti4,
        average_bright_ti4,

        satellites,

        geom,

        centroid_latitude,
        centroid_longitude,

        event_fingerprint,

        status

    )

    VALUES (

        :first_detected_at,
        :last_detected_at,

        :observation_duration_minutes,

        :detection_count,

        :max_frp,
        :average_frp,

        :max_bright_ti4,
        :average_bright_ti4,

        :satellites,

        ST_SetSRID(
            ST_MakePoint(
                :longitude,
                :latitude
            ),
            4326
        ),

        :latitude,
        :longitude,

        :event_fingerprint,

        'active'
    )

    ON CONFLICT (
        event_fingerprint
    )

    DO UPDATE SET

        first_detected_at =
            EXCLUDED.first_detected_at,

        last_detected_at =
            EXCLUDED.last_detected_at,

        observation_duration_minutes =
            EXCLUDED.observation_duration_minutes,

        detection_count =
            EXCLUDED.detection_count,

        max_frp =
            EXCLUDED.max_frp,

        average_frp =
            EXCLUDED.average_frp,

        max_bright_ti4 =
            EXCLUDED.max_bright_ti4,

        average_bright_ti4 =
            EXCLUDED.average_bright_ti4,

        satellites =
            EXCLUDED.satellites,

        geom =
            EXCLUDED.geom,

        centroid_latitude =
            EXCLUDED.centroid_latitude,

        centroid_longitude =
            EXCLUDED.centroid_longitude,

        -- Only advance updated_at when the clustered event's actual
        -- derived inputs changed. This timestamp is the change marker
        -- used by the incremental context/intelligence/risk pipeline.
        updated_at =
            CASE
                WHEN thermal_events.first_detected_at IS DISTINCT FROM EXCLUDED.first_detected_at
                  OR thermal_events.last_detected_at IS DISTINCT FROM EXCLUDED.last_detected_at
                  OR thermal_events.observation_duration_minutes IS DISTINCT FROM EXCLUDED.observation_duration_minutes
                  OR thermal_events.detection_count IS DISTINCT FROM EXCLUDED.detection_count
                  OR thermal_events.max_frp IS DISTINCT FROM EXCLUDED.max_frp
                  OR thermal_events.average_frp IS DISTINCT FROM EXCLUDED.average_frp
                  OR thermal_events.max_bright_ti4 IS DISTINCT FROM EXCLUDED.max_bright_ti4
                  OR thermal_events.average_bright_ti4 IS DISTINCT FROM EXCLUDED.average_bright_ti4
                  OR thermal_events.satellites IS DISTINCT FROM EXCLUDED.satellites
                  OR thermal_events.geom IS DISTINCT FROM EXCLUDED.geom
                  OR thermal_events.centroid_latitude IS DISTINCT FROM EXCLUDED.centroid_latitude
                  OR thermal_events.centroid_longitude IS DISTINCT FROM EXCLUDED.centroid_longitude
                THEN NOW()
                ELSE thermal_events.updated_at
            END

    RETURNING id
    """
)


# ============================================================
# INSERT EVENT → FIRMS DETECTION MAPPING
# ============================================================

INSERT_MAPPING_SQL = text(
    """
    INSERT INTO
        processed.thermal_event_detections (
            event_id,
            firms_event_id
        )

    VALUES (
        :event_id,
        :firms_event_id
    )

    ON CONFLICT (
        event_id,
        firms_event_id
    )

    DO NOTHING
    """
)




# ============================================================
# REMOVE OBSOLETE CURRENT-WINDOW EVENTS
# ============================================================

DELETE_OBSOLETE_CURRENT_EVENTS_SQL = text(
    """
    DELETE FROM processed.thermal_events
    WHERE last_detected_at >= (
        CURRENT_TIMESTAMP - INTERVAL '168 hours'
    )
    AND NOT (event_fingerprint = ANY(:fingerprints))
    """
)


# ============================================================
# REPLACE EVENT → FIRMS DETECTION MAPPINGS
# ============================================================

DELETE_EVENT_MAPPINGS_SQL = text(
    """
    DELETE FROM processed.thermal_event_detections
    WHERE event_id = :event_id
    """
)

# ============================================================
# MAIN REPOSITORY FUNCTION
# ============================================================

def save_thermal_events(events):
    """
    Persist clustered thermal events and their
    FIRMS detection relationships.

    The complete operation runs inside one
    database transaction.
    """

    if not events:
        return 0

    processed_events = 0

    fingerprints = [
        event["event_fingerprint"]
        for event in events
    ]

    with engine.begin() as connection:

        # Reconcile the current 7-day event population.
        # Historical events remain untouched.
        connection.execute(
            DELETE_OBSOLETE_CURRENT_EVENTS_SQL,
            {"fingerprints": fingerprints},
        )

        for event in events:

            # ------------------------------------------------
            # Insert or update event
            # ------------------------------------------------

            result = connection.execute(
                UPSERT_EVENT_SQL,
                {
                    "first_detected_at":
                        event[
                            "first_detected_at"
                        ],

                    "last_detected_at":
                        event[
                            "last_detected_at"
                        ],

                    "observation_duration_minutes":
                        event[
                            "observation_duration_minutes"
                        ],

                    "detection_count":
                        event[
                            "detection_count"
                        ],

                    "max_frp":
                        event[
                            "max_frp"
                        ],

                    "average_frp":
                        event[
                            "average_frp"
                        ],

                    "max_bright_ti4":
                        event[
                            "max_bright_ti4"
                        ],

                    "average_bright_ti4":
                        event[
                            "average_bright_ti4"
                        ],

                    "satellites":
                        event[
                            "satellites"
                        ],

                    "latitude":
                        event[
                            "latitude"
                        ],

                    "longitude":
                        event[
                            "longitude"
                        ],

                    "event_fingerprint":
                        event[
                            "event_fingerprint"
                        ],
                },
            )

            event_id = result.scalar_one()


            # Replace the mapping for this live event so that
            # cluster splits/merges never leave stale detections
            # attached to the event.
            connection.execute(
                DELETE_EVENT_MAPPINGS_SQL,
                {"event_id": event_id},
            )


            # ------------------------------------------------
            # Save raw detection relationships
            # ------------------------------------------------

            for firms_event_id in (
                event["detection_ids"]
            ):

                connection.execute(
                    INSERT_MAPPING_SQL,
                    {
                        "event_id":
                            event_id,

                        "firms_event_id":
                            firms_event_id,
                    },
                )


            processed_events += 1

    return processed_events