from app.services.firms_service import (
    fetch_firms_data,
)


df = fetch_firms_data(
    source="VIIRS_NOAA20_NRT",

    # Maharashtra development area
    west=72.5,
    south=15.5,
    east=80.0,
    north=22.5,

    day_range=5,
)


print("\n========================================")
print("NASA FIRMS HISTORICAL TEST")
print("========================================")

print("\nRecords:")
print(len(df))

if not df.empty:

    print("\nDate range:")

    print(
        df["acq_date"].min(),
        "to",
        df["acq_date"].max(),
    )

    print("\nSatellite:")
    print(
        df["satellite"].value_counts()
    )

    print("\nFirst 10 records:")
    print(
        df.head(10).to_string()
    )

else:

    print("\nNo records returned.")