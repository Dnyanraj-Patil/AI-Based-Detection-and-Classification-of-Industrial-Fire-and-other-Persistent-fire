from app.services.firms_service import fetch_firms_data


df = fetch_firms_data(
    source="VIIRS_SNPP_NRT",

    # Small Pune development bounding box
    west=73.70,
    south=18.40,
    east=74.00,
    north=18.70,

    day_range=1,
)


print("\n========================================")
print("NASA FIRMS TEST")
print("========================================")

print("\nNumber of records:")
print(len(df))

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 records:")
print(df.head().to_string())

print("\nData types:")
print(df.dtypes)