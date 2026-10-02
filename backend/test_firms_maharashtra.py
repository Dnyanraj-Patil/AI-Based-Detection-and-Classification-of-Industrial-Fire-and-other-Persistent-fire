from app.services.firms_service import fetch_firms_data


df = fetch_firms_data(
    source="VIIRS_NOAA21_NRT",

    # Approximate Maharashtra bounding box
    west=72.5,
    south=15.5,
    east=80.0,
    north=22.5,

    day_range=1,
)


print("\n========================================")
print("NASA FIRMS NOAA-21 - MAHARASHTRA TEST")
print("========================================")

print("\nRecords:")
print(len(df))

print("\nColumns:")
print(df.columns.tolist())

if not df.empty:
    print("\nFirst 10 records:")
    print(df.head(10).to_string())

    print("\nGeographic range:")
    print(
        "Latitude:",
        df["latitude"].min(),
        "to",
        df["latitude"].max(),
    )

    print(
        "Longitude:",
        df["longitude"].min(),
        "to",
        df["longitude"].max(),
    )

    print("\nDate range:")
    print(
        df["acq_date"].min(),
        "to",
        df["acq_date"].max(),
    )

else:
    print("\nNo records returned.")