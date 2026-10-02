from sqlalchemy import text

from app.db.database import engine


# ============================================================
# DISTANCE THRESHOLDS
# ============================================================

NEARBY_1KM_METERS = 1000
NEARBY_5KM_METERS = 5000

# Maximum distance considered relevant for industrial context.
CONTEXT_RADIUS_METERS = 10000


# ============================================================
# CALCULATE INDUSTRIAL CONTEXT
# ============================================================

def calculate_event_industrial_context(event_id):
    """
    Calculate industrial context for one thermal event.

    Only industrial facilities within 10 km of the
    thermal event are considered relevant.

    Returns:

        nearest facility
        distance to nearest facility
        facilities within 1 km
        facilities within 5 km
        nearest facility metadata
        industrial-area flag
    """

    query = text(
        """
        WITH event_point AS (

            SELECT
                geom AS geometry,
                geom::geography AS geography

            FROM processed.thermal_events

            WHERE id = :event_id
        ),

        facility_distances AS (

            SELECT

                f.id,

                f.name,

                f.facility_type,

                f.industrial_type,

                ST_Distance(
                    f.geom::geography,
                    e.geography
                ) AS distance_meters,

                CASE
                    WHEN ST_GeometryType(f.geom) IN (
                        'ST_Polygon', 'ST_MultiPolygon'
                    )
                    THEN ST_Covers(f.geom, e.geometry)
                    ELSE FALSE
                END AS contained_by_industrial_area

            FROM raw.industrial_facilities f

            CROSS JOIN event_point e

            WHERE
                f.geom IS NOT NULL

                AND ST_DWithin(
                    f.geom::geography,
                    e.geography,
                    :context_radius
                )
        ),

        statistics AS (

            SELECT

                COUNT(*) FILTER (
                    WHERE distance_meters <= :one_km
                ) AS facilities_within_1km,

                COUNT(*) FILTER (
                    WHERE distance_meters <= :five_km
                ) AS facilities_within_5km,

                COALESCE(
                    BOOL_OR(contained_by_industrial_area),
                    FALSE
                ) AS contains_event

            FROM facility_distances
        ),

        nearest AS (

            SELECT

                id,

                name,

                facility_type,

                industrial_type,

                distance_meters

            FROM facility_distances

            ORDER BY distance_meters

            LIMIT 1
        )

        SELECT

            nearest.id
                AS nearest_facility_id,

            nearest.name
                AS nearest_facility_name,

            nearest.facility_type
                AS nearest_facility_type,

            nearest.industrial_type
                AS nearest_industrial_type,

            nearest.distance_meters
                AS nearest_facility_distance_meters,

            COALESCE(
                statistics.facilities_within_1km,
                0
            ) AS facilities_within_1km,

            COALESCE(
                statistics.facilities_within_5km,
                0
            ) AS facilities_within_5km,

            (
                COALESCE(statistics.contains_event, FALSE)
                OR COALESCE(nearest.distance_meters, 999999) <= 250
            ) AS is_inside_industrial_area

        FROM statistics

        LEFT JOIN nearest
            ON TRUE
        """
    )

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "event_id": event_id,

                "one_km":
                    NEARBY_1KM_METERS,

                "five_km":
                    NEARBY_5KM_METERS,

                "context_radius":
                    CONTEXT_RADIUS_METERS,
            },
        )

        row = result.mappings().first()

    if row is None:
        return None

    return dict(row)


# ============================================================
# SAVE INDUSTRIAL CONTEXT
# ============================================================

def save_event_industrial_context(
    event_id,
    context,
):
    """
    Insert or update industrial context
    for one thermal event.
    """

    if context is None:
        return False

    query = text(
        """
        INSERT INTO
            processed.event_industrial_context (

                event_id,

                nearest_facility_id,

                nearest_facility_distance_meters,

                facilities_within_1km,

                facilities_within_5km,

                nearest_facility_name,

                nearest_facility_type,

                nearest_industrial_type,

                is_inside_industrial_area

            )

        VALUES (

            :event_id,

            :nearest_facility_id,

            :nearest_facility_distance_meters,

            :facilities_within_1km,

            :facilities_within_5km,

            :nearest_facility_name,

            :nearest_facility_type,

            :nearest_industrial_type,

            :is_inside_industrial_area

        )

        ON CONFLICT (event_id)

        DO UPDATE SET

            nearest_facility_id =
                EXCLUDED.nearest_facility_id,

            nearest_facility_distance_meters =
                EXCLUDED.nearest_facility_distance_meters,

            facilities_within_1km =
                EXCLUDED.facilities_within_1km,

            facilities_within_5km =
                EXCLUDED.facilities_within_5km,

            nearest_facility_name =
                EXCLUDED.nearest_facility_name,

            nearest_facility_type =
                EXCLUDED.nearest_facility_type,

            nearest_industrial_type =
                EXCLUDED.nearest_industrial_type,

            is_inside_industrial_area =
                EXCLUDED.is_inside_industrial_area,

            updated_at =
                NOW()
        """
    )

    with engine.begin() as connection:

        connection.execute(
            query,
            {
                "event_id":
                    event_id,

                "nearest_facility_id":
                    context[
                        "nearest_facility_id"
                    ],

                "nearest_facility_distance_meters":
                    context[
                        "nearest_facility_distance_meters"
                    ],

                "facilities_within_1km":
                    context[
                        "facilities_within_1km"
                    ],

                "facilities_within_5km":
                    context[
                        "facilities_within_5km"
                    ],

                "nearest_facility_name":
                    context[
                        "nearest_facility_name"
                    ],

                "nearest_facility_type":
                    context[
                        "nearest_facility_type"
                    ],

                "nearest_industrial_type":
                    context[
                        "nearest_industrial_type"
                    ],

                "is_inside_industrial_area":
                    context[
                        "is_inside_industrial_area"
                    ],
            },
        )

    return True


# ============================================================
# PROCESS ALL EVENTS
# ============================================================

def process_all_event_industrial_context():
    """
    Calculate and save industrial context only for thermal events
    that do not already have a context record.

    Existing context is preserved. Recalculation is triggered only when
    a thermal event is new or its clustered inputs actually changed.
    """

    event_query = text(
        """
        SELECT e.id

        FROM processed.thermal_events e

        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '168 hours'
        )

        AND (
            NOT EXISTS (
                SELECT 1
                FROM processed.event_industrial_context c
                WHERE c.event_id = e.id
            )
            OR EXISTS (
                SELECT 1
                FROM processed.event_industrial_context c
                WHERE c.event_id = e.id
                  AND e.updated_at > c.updated_at
            )
        )

        ORDER BY e.id
        """
    )

    with engine.connect() as connection:

        events = (
            connection.execute(
                event_query
            )
            .scalars()
            .all()
        )

    processed = 0

    for event_id in events:

        context = (
            calculate_event_industrial_context(
                event_id
            )
        )

        if context is None:
            continue

        save_event_industrial_context(
            event_id,
            context,
        )

        processed += 1

    return processed