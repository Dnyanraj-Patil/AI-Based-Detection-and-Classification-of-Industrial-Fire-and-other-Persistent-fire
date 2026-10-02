from sqlalchemy import text

from app.db.database import engine


OSM_SOURCE = "OpenStreetMap"


def insert_industrial_facilities(df):
    """
    Insert or update normalized OpenStreetMap
    industrial facilities into PostGIS.

    Expected DataFrame columns:

        osm_type
        osm_id
        name
        landuse
        industrial
        man_made
        building
        power
        latitude
        longitude
        geometry_wkt
    """

    if df is None or df.empty:
        return {
            "processed": 0,
            "inserted_or_updated": 0,
            "skipped": 0,
        }

    required_columns = [
        "osm_type",
        "osm_id",
        "name",
        "landuse",
        "industrial",
        "man_made",
        "latitude",
        "longitude",
        "geometry_wkt",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required OSM columns: "
            + ", ".join(missing_columns)
        )

    # OSM tags are sparse by design. Not every object has building/power
    # tags, so these two enrichment fields must never be required for an
    # object to be inserted. Normalize absent columns to null explicitly.
    for optional_column in ("building", "power"):
        if optional_column not in df.columns:
            df[optional_column] = None

    insert_query = text(
        """
        INSERT INTO raw.industrial_facilities (

            osm_type,
            osm_id,
            name,
            facility_type,
            industrial_type,
            latitude,
            longitude,
            geom,
            source,
            source_url,
            fetched_at

        )

        VALUES (

            :osm_type,
            :osm_id,
            :name,
            :facility_type,
            :industrial_type,
            :latitude,
            :longitude,

            ST_SetSRID(
                ST_GeomFromText(
                    :geometry_wkt,
                    4326
                ),
                4326
            ),

            :source,
            :source_url,
            NOW()

        )

        ON CONFLICT (
            osm_type,
            osm_id
        )

        DO UPDATE SET

            name =
                EXCLUDED.name,

            facility_type =
                EXCLUDED.facility_type,

            industrial_type =
                EXCLUDED.industrial_type,

            latitude =
                EXCLUDED.latitude,

            longitude =
                EXCLUDED.longitude,

            geom =
                EXCLUDED.geom,

            source =
                EXCLUDED.source,

            source_url =
                EXCLUDED.source_url,

            fetched_at =
                NOW()
        """
    )

    processed = 0
    skipped = 0

    with engine.begin() as connection:

        for _, row in df.iterrows():

            geometry_wkt = row["geometry_wkt"]

            if (
                geometry_wkt is None
                or str(geometry_wkt).strip() == ""
            ):
                skipped += 1
                continue

            osm_type = row["osm_type"]
            osm_id = row["osm_id"]

            if (
                osm_type is None
                or osm_id is None
            ):
                skipped += 1
                continue

            # ------------------------------------------------
            # Facility classification
            # ------------------------------------------------

            landuse = row["landuse"]
            industrial = row["industrial"]
            man_made = row["man_made"]
            building = row.get("building")
            power = row.get("power")

            facility_type = None

            if (
                landuse is not None
                and str(landuse).strip()
                != ""
            ):
                facility_type = str(
                    landuse
                )

            elif (
                building is not None
                and str(building).strip()
                != ""
            ):
                facility_type = str(building)

            elif (
                power is not None
                and str(power).strip()
                != ""
            ):
                facility_type = str(power)

            elif (
                man_made is not None
                and str(man_made).strip()
                != ""
            ):
                facility_type = str(man_made)

            industrial_type = None

            if (
                industrial is not None
                and str(industrial).strip()
                != ""
            ):
                industrial_type = str(
                    industrial
                )

            # ------------------------------------------------
            # Name
            # ------------------------------------------------

            name = row["name"]

            if name is not None:

                name = str(name).strip()

                if name == "":
                    name = None

            # ------------------------------------------------
            # Source URL
            # ------------------------------------------------

            source_url = (
                f"https://www.openstreetmap.org/"
                f"{osm_type}/{int(osm_id)}"
            )

            # ------------------------------------------------
            # Execute
            # ------------------------------------------------

            connection.execute(
                insert_query,
                {
                    "osm_type": str(
                        osm_type
                    ),

                    "osm_id": int(
                        osm_id
                    ),

                    "name": name,

                    "facility_type":
                        facility_type,

                    "industrial_type":
                        industrial_type,

                    "latitude":
                        float(
                            row["latitude"]
                        ),

                    "longitude":
                        float(
                            row["longitude"]
                        ),

                    "geometry_wkt":
                        str(
                            geometry_wkt
                        ),

                    "source":
                        OSM_SOURCE,

                    "source_url":
                        source_url,
                },
            )

            processed += 1

    return {
        "processed": processed,
        "inserted_or_updated": processed,
        "skipped": skipped,
    }