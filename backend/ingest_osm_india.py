"""India-wide OpenStreetMap industrial baseline ingestion.

The SIH solution needs OSM industrial context across the monitored country,
not only around today's thermal hotspots. This job covers India's geographic
extent in manageable Overpass tiles, deduplicates OSM objects, and upserts the
live result into PostGIS.
"""
from __future__ import annotations

import time
import pandas as pd

from app.services.osm_service import fetch_industrial_facilities
from app.services.osm_repository import insert_industrial_facilities

# Geographic envelope covering mainland India plus Lakshadweep and Andaman/Nicobar.
INDIA_WEST = 68.0
INDIA_SOUTH = 6.0
INDIA_EAST = 97.5
INDIA_NORTH = 35.7

# Small enough to keep Overpass requests reliable while providing nationwide coverage.
TILE_WIDTH = 6.0
TILE_HEIGHT = 5.0
TARGET_FACILITIES = 10000


def tiles():
    lat = INDIA_SOUTH
    while lat < INDIA_NORTH:
        north = min(lat + TILE_HEIGHT, INDIA_NORTH)
        lon = INDIA_WEST
        while lon < INDIA_EAST:
            east = min(lon + TILE_WIDTH, INDIA_EAST)
            yield lon, lat, east, north
            lon = east
        lat = north


def main():
    all_frames = []
    tile_list = list(tiles())
    print("\n========================================")
    print("THERMOINTEL INDIA-WIDE OSM INGESTION")
    print("========================================")
    print(f"Coverage: {INDIA_WEST},{INDIA_SOUTH} to {INDIA_EAST},{INDIA_NORTH}")
    print(f"Tiles: {len(tile_list)}")

    for i, (west, south, east, north) in enumerate(tile_list, 1):
        print(f"[OSM {i}/{len(tile_list)}] bbox={west},{south},{east},{north}")
        try:
            frame = fetch_industrial_facilities(west, south, east, north)
            if not frame.empty:
                all_frames.append(frame)
                print(f"  received {len(frame)} objects")
            else:
                print("  received 0 objects")
        except Exception as exc:
            print(f"  tile failed: {exc}")
        time.sleep(1)

    if not all_frames:
        raise RuntimeError("No OSM industrial facilities were returned from any India tile.")

    df = pd.concat(all_frames, ignore_index=True)
    df = df.drop_duplicates(subset=["osm_type", "osm_id"]).reset_index(drop=True)

    # OSM tags are sparse: a facility may have neither a building nor power tag.
    # Keep those fields in the ingestion frame as nullable enrichment columns so
    # the repository can safely insert every valid OSM facility.
    for optional_column in ("building", "power"):
        if optional_column not in df.columns:
            df[optional_column] = None

    print(f"\nUnique India-wide OSM facilities: {len(df)}")
    if len(df) < TARGET_FACILITIES:
        print(f"NOTE: OSM returned fewer than {TARGET_FACILITIES} objects; no synthetic facilities are created.")

    result = insert_industrial_facilities(df)
    print("\n========================================")
    print("OSM INDIA INGESTION COMPLETE")
    print("========================================")
    print(result)


if __name__ == "__main__":
    main()
