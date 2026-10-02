from app.services.firms_service import (
    fetch_firms_data,
)

from app.services.firms_normalizer import (
    normalize_firms_dataframe,
)

from app.services.firms_repository import (
    insert_firms_dataframe,
)


def main():

    print("========================================")
    print("THERMOINTEL HISTORICAL FIRMS INGESTION")
    print("========================================")

    print(
        "\n[1/3] Fetching FIRMS history..."
    )

    raw_df = fetch_firms_data(
        source="VIIRS_NOAA20_NRT",
        west=72.5,
        south=15.5,
        east=80.0,
        north=22.5,
        day_range=5,
    )

    print(
        f"Received {len(raw_df)} records."
    )

    print(
        "\n[2/3] Normalizing..."
    )

    normalized_df = (
    normalize_firms_dataframe(
        raw_df,
        "VIIRS_NOAA20_NRT"
    )
)

    print(
        f"Validated "
        f"{len(normalized_df)} records."
    )

    print(
        "\n[3/3] Inserting into PostGIS..."
    )

    processed = insert_firms_dataframe(
        normalized_df
    )

    print(
        f"Processed {processed} records."
    )

    print(
        "\n========================================"
    )

    print(
        "HISTORICAL INGESTION COMPLETE"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()