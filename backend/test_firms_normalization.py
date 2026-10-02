from app.services.firms_service import fetch_firms_data
from app.services.firms_normalizer import (
    normalize_firms_dataframe,
)


df = fetch_firms_data(
    source="VIIRS_SNPP_NRT",
    west=73.70,
    south=18.40,
    east=74.00,
    north=18.70,
    day_range=1,
)


normalized = normalize_firms_dataframe(
    df,
    source="VIIRS_SNPP_NRT",
)


print("\n========================================")
print("NORMALIZED FIRMS DATA")
print("========================================")

print("\nRecords:")
print(len(normalized))

print("\nColumns:")
print(normalized.columns.tolist())

print("\nData types:")
print(normalized.dtypes)

print("\nSample:")
print(
    normalized.head(5).to_string()
)

print("\nTimestamp:")
print(
    normalized[
        [
            "acquisition_date",
            "acquisition_time",
            "acquisition_datetime",
        ]
    ].head()
)