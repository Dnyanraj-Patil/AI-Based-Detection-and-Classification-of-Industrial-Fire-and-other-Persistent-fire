import hashlib

from sqlalchemy import text

from app.db.database import engine


# ============================================================
# CLUSTERING CONFIGURATION
# ============================================================

CLUSTER_RADIUS_METERS = 1500
CLUSTER_TIME_HOURS = 3
CURRENT_EVENT_WINDOW_HOURS = 168


# ============================================================
# EVENT FINGERPRINT
# ============================================================

def generate_event_fingerprint(detection_ids):
    """
    Generate a stable deterministic SHA-256 fingerprint
    from the earliest FIRMS detection ID (the cluster anchor).

    Using the anchor rather than the complete detection list is
    important for live ingestion: a growing cluster keeps the
    same event identity as new detections arrive.
    """

    normalized_ids = sorted(
        int(value)
        for value in detection_ids
    )

    if not normalized_ids:
        raise ValueError("An event fingerprint requires at least one detection ID.")

    # The smallest detection ID is the deterministic cluster anchor.
    value = str(normalized_ids[0])

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


# ============================================================
# BUILD SPATIAL-TEMPORAL CLUSTERS
# ============================================================

def build_detection_clusters():
    """
    Build spatial-temporal clusters from raw FIRMS
    detections.

    Two detections are connected when:

        1. They are within 1.5 km.
        2. Their acquisition times are within 3 hours.

    Connected detections form one thermal event.
    """

    query = text(
        """
        WITH RECURSIVE

        current_detections AS (

            SELECT *
            FROM raw.firms_events
            WHERE acquisition_datetime >= (
                CURRENT_TIMESTAMP -
                (:window_hours * INTERVAL '1 hour')
            )
        ),

        edges AS (

            SELECT
                a.id AS source_id,
                b.id AS target_id

            FROM current_detections a

            JOIN current_detections b
                ON a.id < b.id

            WHERE

                ABS(
                    EXTRACT(
                        EPOCH FROM (
                            a.acquisition_datetime
                            - b.acquisition_datetime
                        )
                    )
                ) <= :time_seconds

                AND ST_DWithin(
                    a.geom::geography,
                    b.geom::geography,
                    :radius_meters
                )
        ),

        graph AS (

            -- Every detection is initially
            -- its own component.

            SELECT
                id,
                id AS component_id

            FROM current_detections


            UNION


            -- Forward edge

            SELECT
                e.target_id,
                e.source_id

            FROM edges e


            UNION


            -- Reverse edge

            SELECT
                e.source_id,
                e.target_id

            FROM edges e
        ),

        reachability AS (

            SELECT
                id,
                component_id

            FROM graph


            UNION


            SELECT
                r.id,
                g.component_id

            FROM reachability r

            JOIN graph g
                ON r.component_id = g.id
        )

        SELECT DISTINCT

            id,

            MIN(component_id)
                OVER (
                    PARTITION BY id
                ) AS cluster_id

        FROM reachability
        """
    )

    with engine.connect() as connection:

        rows = (
            connection.execute(
                query,
                {
                    "radius_meters":
                        CLUSTER_RADIUS_METERS,

                    "time_seconds":
                        CLUSTER_TIME_HOURS * 3600,

                    "window_hours":
                        CURRENT_EVENT_WINDOW_HOURS,
                },
            )
            .mappings()
            .all()
        )

    return rows


# ============================================================
# AGGREGATE CLUSTERS
# ============================================================

def aggregate_clusters(cluster_rows):
    """
    Convert detection-level cluster assignments
    into event-level summaries.
    """

    if not cluster_rows:
        return []


    # --------------------------------------------------------
    # Group detection IDs by cluster
    # --------------------------------------------------------

    cluster_ids = {}

    for row in cluster_rows:

        cluster_id = row["cluster_id"]

        if cluster_id not in cluster_ids:

            cluster_ids[cluster_id] = []

        cluster_ids[cluster_id].append(
            row["id"]
        )


    results = []


    # --------------------------------------------------------
    # Retrieve raw detection information
    # --------------------------------------------------------

    detection_query = text(
        """
        SELECT

            id,

            acquisition_datetime,

            latitude,

            longitude,

            geom,

            frp,

            bright_ti4,

            satellite

        FROM raw.firms_events

        WHERE id = ANY(:ids)

        ORDER BY
            acquisition_datetime,
            id
        """
    )


    with engine.connect() as connection:

        for cluster_id, ids in cluster_ids.items():

            rows = (
                connection.execute(
                    detection_query,
                    {
                        "ids": ids
                    },
                )
                .mappings()
                .all()
            )


            if not rows:
                continue


            # ------------------------------------------------
            # FRP values
            # ------------------------------------------------

            frp_values = [

                float(row["frp"])

                for row in rows

                if row["frp"] is not None
            ]


            # ------------------------------------------------
            # Brightness temperature values
            # ------------------------------------------------

            bright_values = [

                float(row["bright_ti4"])

                for row in rows

                if row["bright_ti4"] is not None
            ]


            # ------------------------------------------------
            # Satellites
            # ------------------------------------------------

            satellites = sorted(
                {
                    row["satellite"]

                    for row in rows

                    if row["satellite"]
                }
            )


            # ------------------------------------------------
            # First / last observation
            # ------------------------------------------------

            first_detected_at = min(
                row["acquisition_datetime"]

                for row in rows
            )


            last_detected_at = max(
                row["acquisition_datetime"]

                for row in rows
            )


            # ------------------------------------------------
            # Observation duration
            #
            # IMPORTANT:
            # This is observation span, NOT actual
            # fire duration.
            # ------------------------------------------------

            observation_duration_minutes = (

                (
                    last_detected_at
                    - first_detected_at
                ).total_seconds()

                / 60
            )


            # ------------------------------------------------
            # Average latitude
            # ------------------------------------------------

            avg_latitude = (

                sum(
                    row["latitude"]
                    for row in rows
                )

                / len(rows)
            )


            # ------------------------------------------------
            # Average longitude
            # ------------------------------------------------

            avg_longitude = (

                sum(
                    row["longitude"]
                    for row in rows
                )

                / len(rows)
            )


            # ------------------------------------------------
            # Detection IDs
            # ------------------------------------------------

            detection_ids = sorted(
                int(row["id"])
                for row in rows
            )


            # ------------------------------------------------
            # Deterministic event fingerprint
            # ------------------------------------------------

            event_fingerprint = (
                generate_event_fingerprint(
                    detection_ids
                )
            )


            # ------------------------------------------------
            # Create event summary
            # ------------------------------------------------

            results.append(
                {

                    "cluster_id":
                        cluster_id,


                    "first_detected_at":
                        first_detected_at,


                    "last_detected_at":
                        last_detected_at,


                    "observation_duration_minutes":
                        observation_duration_minutes,


                    "detection_count":
                        len(rows),


                    "max_frp":
                        (
                            max(frp_values)
                            if frp_values
                            else None
                        ),


                    "average_frp":
                        (
                            sum(frp_values)
                            / len(frp_values)
                        )
                        if frp_values
                        else None,


                    "max_bright_ti4":
                        (
                            max(bright_values)
                            if bright_values
                            else None
                        ),


                    "average_bright_ti4":
                        (
                            sum(bright_values)
                            / len(bright_values)
                        )
                        if bright_values
                        else None,


                    "satellites":
                        satellites,


                    "latitude":
                        avg_latitude,


                    "longitude":
                        avg_longitude,


                    "detection_ids":
                        detection_ids,


                    "event_fingerprint":
                        event_fingerprint,
                }
            )


    return results


# ============================================================
# MAIN CLUSTERING FUNCTION
# ============================================================

def cluster_firms_events():
    """
    Execute the complete FIRMS clustering pipeline.

    Returns:
        List of aggregated thermal events.
    """

    cluster_rows = (
        build_detection_clusters()
    )

    return aggregate_clusters(
        cluster_rows
    )