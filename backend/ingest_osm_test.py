from app.services.osm_service import (
    fetch_industrial_facilities,
)

from app.services.osm_repository import (
    insert_industrial_facilities,
)


# ============================================================
# MAHARASHTRA DEVELOPMENT BOUNDING BOX
# ============================================================

WEST = 72.5
SOUTH = 15.5
EAST = 81.0
NORTH = 22.5


def main():

    print("=" * 40)
    print("THERMOINTEL OSM INGESTION")
    print("=" * 40)

    # --------------------------------------------------------
    # 1. Fetch
    # --------------------------------------------------------

    print()
    print("[1/3] Fetching OpenStreetMap data...")

    df = fetch_industrial_facilities(
        west=WEST,
        south=SOUTH,
        east=EAST,
        north=NORTH,
    )

    print(
        f"Received {len(df)} records."
    )

    if df.empty:

        print(
            "No OSM records received."
        )

        return

    # --------------------------------------------------------
    # 2. Validate
    # --------------------------------------------------------

    print()
    print("[2/3] Validating OSM data...")

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

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing columns: "
            + ", ".join(missing)
        )

    valid_df = df[
        df["osm_type"].notna()
        & df["osm_id"].notna()
        & df["geometry_wkt"].notna()
    ].copy()

    print(
        f"Validated {len(valid_df)} records."
    )

    # --------------------------------------------------------
    # 3. Insert
    # --------------------------------------------------------

    print()
    print(
        "[3/3] Inserting into PostGIS..."
    )

    result = insert_industrial_facilities(
        valid_df
    )

    print(
        f"Processed: "
        f"{result['processed']}"
    )

    print(
        f"Inserted/updated: "
        f"{result['inserted_or_updated']}"
    )

    print(
        f"Skipped: "
        f"{result['skipped']}"
    )

    print()
    print("=" * 40)
    print(
        "OSM INGESTION COMPLETE"
    )
    print("=" * 40)


if __name__ == "__main__":
    main()