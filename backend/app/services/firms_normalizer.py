import pandas as pd


REQUIRED_COLUMNS = [
    "latitude",
    "longitude",
    "bright_ti4",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_ti5",
    "frp",
    "daynight",
]


def validate_firms_schema(df: pd.DataFrame) -> None:
    """
    Verify that the FIRMS response contains
    all fields required by ThermoIntel.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required FIRMS columns: "
            f"{missing_columns}"
        )


def normalize_firms_dataframe(
    df: pd.DataFrame,
    source: str,
) -> pd.DataFrame:
    """
    Convert raw FIRMS data into ThermoIntel's
    internal normalized format.
    """

    # -------------------------------------------------
    # 1. Validate schema
    # -------------------------------------------------

    validate_firms_schema(df)

    result = df.copy()

    # -------------------------------------------------
    # 2. Normalize column names
    # -------------------------------------------------

    result = result.rename(
        columns={
            "acq_date": "acquisition_date",
            "acq_time": "acquisition_time",
            "bright_ti4": "brightness_temperature_i4",
            "bright_ti5": "brightness_temperature_i5",
        }
    )

    # -------------------------------------------------
    # 3. Validate coordinates
    # -------------------------------------------------

    result["latitude"] = pd.to_numeric(
        result["latitude"],
        errors="coerce",
    )

    result["longitude"] = pd.to_numeric(
        result["longitude"],
        errors="coerce",
    )

    result = result[
        result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    ]

    # -------------------------------------------------
    # 4. Normalize numerical measurements
    # -------------------------------------------------

    numerical_columns = [
        "brightness_temperature_i4",
        "brightness_temperature_i5",
        "scan",
        "track",
        "frp",
    ]

    for column in numerical_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    # -------------------------------------------------
    # 5. Create UTC timestamp
    # -------------------------------------------------

    result["acquisition_datetime"] = pd.to_datetime(
        result["acquisition_date"].astype(str)
        + " "
        + result["acquisition_time"]
        .astype(str)
        .str.zfill(4),
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )

    # -------------------------------------------------
    # 6. Remove invalid timestamps
    # -------------------------------------------------

    result = result.dropna(
        subset=[
            "latitude",
            "longitude",
            "acquisition_datetime",
        ]
    )

    # -------------------------------------------------
    # 7. Add source metadata
    # -------------------------------------------------

    result["source"] = source

    # -------------------------------------------------
    # 8. Remove exact duplicate observations
    # -------------------------------------------------

    result = result.drop_duplicates(
        subset=[
            "latitude",
            "longitude",
            "acquisition_datetime",
            "satellite",
            "instrument",
            "version",
        ]
    )

    # -------------------------------------------------
    # 9. Reset index
    # -------------------------------------------------

    result = result.reset_index(drop=True)

    return result