import pandas as pd


REQUIRED_COLUMNS = [
    "osm_type",
    "osm_id",
    "latitude",
    "longitude",
    "geometry_wkt",
]


def validate_osm_schema(
    df: pd.DataFrame,
) -> None:

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing OSM columns: {missing}"
        )


def normalize_osm_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:

    validate_osm_schema(df)

    result = df.copy()

    # ---------------------------------------------
    # Numeric conversion
    # ---------------------------------------------

    result["latitude"] = pd.to_numeric(
        result["latitude"],
        errors="coerce",
    )

    result["longitude"] = pd.to_numeric(
        result["longitude"],
        errors="coerce",
    )

    # ---------------------------------------------
    # Coordinate validation
    # ---------------------------------------------

    result = result[
        result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    ]

    # ---------------------------------------------
    # Remove objects without geometry
    # ---------------------------------------------

    result = result.dropna(
        subset=[
            "latitude",
            "longitude",
            "geometry_wkt",
        ]
    )

    # ---------------------------------------------
    # Remove duplicate OSM objects
    # ---------------------------------------------

    result = result.drop_duplicates(
        subset=[
            "osm_type",
            "osm_id",
        ]
    )

    # ---------------------------------------------
    # Normalize missing text
    # ---------------------------------------------

    for column in [
        "name",
        "landuse",
        "industrial",
        "man_made",
    ]:

        if column in result.columns:

            result[column] = (
                result[column]
                .where(
                    result[column].notna(),
                    None,
                )
            )

    return result.reset_index(drop=True)