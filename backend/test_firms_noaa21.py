from app.services.firms_service import fetch_firms_data


df = fetch_firms_data(
    source="VIIRS_NOAA21_NRT",
    west=73.70,
    south=18.40,
    east=74.00,
    north=18.70,
    day_range=1,
)

print("\n========================================")
print("NASA FIRMS NOAA-21 TEST")
print("========================================")

print("\nRecords:")
print(len(df))

print("\nColumns:")
print(df.columns.tolist())

if not df.empty:
    print("\nFirst 5 records:")
    print(df.head().to_string())
else:
    print("\nNo records returned.")