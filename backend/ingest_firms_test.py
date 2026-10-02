from app.services.firms_service import fetch_firms_data
from app.services.firms_normalizer import (
    normalize_firms_dataframe,
)
from app.services.firms_repository import (
    insert_firms_dataframe,
)


SOURCE = "VIIRS_NOAA20_NRT"
def main():

    print("========================================")
    print("THERMOINTEL FIRMS INGESTION")
    print("========================================")

    print("\n[1/3] Fetching NASA FIRMS data...")

    raw_df = fetch_firms_data(
    source=SOURCE,
    west=72.5,
    south=15.5,
    east=80.0,
    north=22.5,
    day_range=1,
)

    print(
        f"Received {len(raw_df)} records."
    )

    print("\n[2/3] Normalizing data...")

    normalized_df = normalize_firms_dataframe(
        raw_df,
        source=SOURCE,
    )

    print(
        f"Validated {len(normalized_df)} records."
    )

    print("\n[3/3] Inserting into PostGIS...")

    inserted = insert_firms_dataframe(
        normalized_df
    )

    print(
        f"Processed {inserted} records."
    )

    print("\n========================================")
    print("INGESTION COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()