from app.services.osm_service import (
    fetch_industrial_facilities,
)


print("\n========================================")
print("THERMOINTEL OSM DATA QUALITY CHECK")
print("========================================")


df = fetch_industrial_facilities(
    west=72.0,
    south=15.0,
    east=80.0,
    north=22.0,
)


print(
    f"\nTotal records: {len(df)}"
)


print("\nRecords by OSM type:")

print(
    df["osm_type"]
    .value_counts()
    .to_string()
)


print("\nRecords by landuse:")

print(
    df["landuse"]
    .fillna("NULL")
    .value_counts()
    .head(20)
    .to_string()
)


print("\nRecords by industrial:")

print(
    df["industrial"]
    .fillna("NULL")
    .value_counts()
    .head(20)
    .to_string()
)


print("\nRecords by man_made:")

print(
    df["man_made"]
    .fillna("NULL")
    .value_counts()
    .head(20)
    .to_string()
)


print("\nRecords without names:")

print(
    df["name"]
    .isna()
    .sum()
)


print("\nRecords with names:")

print(
    df["name"]
    .notna()
    .sum()
)


print("\nDuplicate OSM objects:")

duplicates = df.duplicated(
    subset=[
        "osm_type",
        "osm_id",
    ]
).sum()

print(duplicates)


print("\n========================================")
print("OSM QUALITY CHECK COMPLETE")
print("========================================")