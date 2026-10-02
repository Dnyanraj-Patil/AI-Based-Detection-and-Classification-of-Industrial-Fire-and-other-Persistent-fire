from app.services.osm_service import (
    fetch_industrial_facilities,
)


print("\n========================================")
print("OPENSTREETMAP INDUSTRIAL FACILITIES")
print("========================================")


df = fetch_industrial_facilities(
    west=72.0,
    south=15.0,
    east=80.0,
    north=22.0,
)


print("\nRecords:")
print(len(df))


print("\nColumns:")
print(df.columns.tolist())


print("\nFirst 20 records:")

print(
    df.head(20).to_string(
        index=False
    )
)


print("\n========================================")
print("OSM TEST COMPLETE")
print("========================================")