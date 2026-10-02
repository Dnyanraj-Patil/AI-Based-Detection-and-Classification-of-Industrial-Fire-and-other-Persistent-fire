"""Satellite-derived land-cover enrichment for ThermoIntel.

Primary source: ESA WorldCover 2021 v200, a 10 m global land-cover product
built from Sentinel-1 and Sentinel-2 data.  OSM is retained only as a fallback
context source when the WorldCover COG cannot be reached.
"""
from __future__ import annotations

import math
import os
from collections import Counter
from functools import lru_cache

import requests
from sqlalchemy import text
from app.db.database import engine

try:
    import rasterio
    from rasterio.windows import Window
except Exception:  # pragma: no cover - dependency is installed in production
    rasterio = None
    Window = None

OVERPASS_URLS = [
    os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
    "https://overpass.kumi.systems/api/interpreter",
]
RADIUS_METERS = int(os.getenv("LANDCOVER_RADIUS_METERS", "500"))
TIMEOUT_SECONDS = int(os.getenv("LANDCOVER_TIMEOUT_SECONDS", "20"))
WORLD_COVER_TIMEOUT_SECONDS = int(os.getenv("WORLDCOVER_TIMEOUT_SECONDS", "30"))
SAMPLE_RADIUS_PIXELS = int(os.getenv("WORLDCOVER_SAMPLE_RADIUS_PIXELS", "3"))
WORLD_COVER_BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"

# ESA WorldCover 2021 v200 map codes.
WORLD_COVER_CLASSES = {
    10: "TREE_COVER",
    20: "SHRUBLAND",
    30: "GRASSLAND",
    40: "CROPLAND",
    50: "BUILT_UP",
    60: "BARE_SPARSE_VEGETATION",
    70: "SNOW_ICE",
    80: "PERMANENT_WATER",
    90: "HERBACEOUS_WETLAND",
    95: "MANGROVES",
    100: "MOSS_LICHEN",
}

# Context categories used by the classifier. WorldCover deliberately does not
# have an "industrial" class, so industrial evidence remains OSM-based.
VEGETATION_CLASSES = {"TREE_COVER", "SHRUBLAND", "GRASSLAND", "HERBACEOUS_WETLAND", "MANGROVES", "MOSS_LICHEN"}
AGRICULTURE_CLASSES = {"CROPLAND"}
BUILT_CLASSES = {"BUILT_UP"}

CLASS_RULES = {
    "FOREST": {"natural": {"wood", "forest"}, "landuse": {"forest"}},
    "SHRUB_GRASS": {"natural": {"scrub", "heath", "grassland"}, "landuse": {"grass"}},
    "AGRICULTURE": {"landuse": {"farmland", "farm", "orchard", "vineyard", "plant_nursery"}},
    "WETLAND": {"natural": {"wetland", "marsh", "mud"}},
    "WATER": {"natural": {"water"}, "water": {"lake", "reservoir", "pond"}},
    "INDUSTRIAL": {"landuse": {"industrial"}},
    "BUILT_UP": {"landuse": {"residential", "commercial", "retail"}, "building": {"yes"}},
}


def _tile_name(latitude: float, longitude: float) -> str:
    """Return the 3x3-degree ESA WorldCover tile containing a point."""
    lat0 = math.floor(float(latitude) / 3.0) * 3
    lon0 = math.floor(float(longitude) / 3.0) * 3
    lat_prefix = "N" if lat0 >= 0 else "S"
    lon_prefix = "E" if lon0 >= 0 else "W"
    return f"{lat_prefix}{abs(lat0):02d}{lon_prefix}{abs(lon0):03d}"


@lru_cache(maxsize=16)
def _open_worldcover(tile: str):
    """Open and cache a WorldCover COG; GDAL performs HTTP range reads."""
    if rasterio is None:
        raise RuntimeError("rasterio is not installed")
    url = f"{WORLD_COVER_BASE}/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
    env = rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    )
    env.__enter__()
    try:
        dataset = rasterio.open(f"/vsicurl/{url}")
        return env, dataset
    except Exception:
        env.__exit__(None, None, None)
        raise


def _worldcover_sample(latitude: float, longitude: float):
    """Sample a small neighbourhood around an event centroid from WorldCover."""
    tile = _tile_name(latitude, longitude)
    env, dataset = _open_worldcover(tile)
    try:
        row, col = dataset.index(float(longitude), float(latitude))
        radius = max(0, SAMPLE_RADIUS_PIXELS)
        size = radius * 2 + 1
        window = Window(col - radius, row - radius, size, size)
        values = dataset.read(1, window=window, boundless=True, masked=True)
        vals = [int(v) for v in values.compressed() if int(v) in WORLD_COVER_CLASSES]
        if not vals:
            return None
        counts = Counter(vals)
        code, count = counts.most_common(1)[0]
        klass = WORLD_COVER_CLASSES[code]
        total = sum(counts.values())
        purity = count / max(total, 1)
        # The class is authoritative at 10 m, while this confidence measures
        # local neighbourhood agreement and is never presented as fire-cause probability.
        confidence = min(0.60 + 0.40 * purity, 0.98)
        return {
            "class": klass,
            "confidence": round(confidence, 3),
            "source": "ESA_WORLDCOVER_2021_V200",
            "evidence": {
                "tile": tile,
                "resolution_m": 10,
                "sample_pixels": total,
                "class_counts": {WORLD_COVER_CLASSES[k]: v for k, v in counts.items()},
                "dominant_fraction": round(purity, 3),
            },
        }
    finally:
        # Keep the GDAL dataset cache warm; closing here would defeat the LRU.
        # The environment remains attached to the cached dataset for the process lifetime.
        pass


def _classify_tags(tags):
    scores = {}
    for key, value in tags.items():
        value = str(value).lower()
        for klass, rules in CLASS_RULES.items():
            if value in rules.get(key, set()):
                scores[klass] = scores.get(klass, 0) + 1
    if not scores:
        return "UNKNOWN", 0.0
    klass = max(scores, key=scores.get)
    confidence = min(0.55 + 0.15 * (scores[klass] - 1), 0.85)
    return klass, confidence


def _fetch_osm_fallback(latitude, longitude):
    q = f"""
    [out:json][timeout:15];
    (
      way(around:{RADIUS_METERS},{latitude},{longitude})[landuse];
      relation(around:{RADIUS_METERS},{latitude},{longitude})[landuse];
      way(around:{RADIUS_METERS},{latitude},{longitude})[natural];
      relation(around:{RADIUS_METERS},{latitude},{longitude})[natural];
    );
    out tags center 80;
    """
    last_error = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(url, data=q, timeout=TIMEOUT_SECONDS,
                              headers={"User-Agent": "ThermoIntel/3.0 SIH26162"})
            r.raise_for_status()
            data = r.json()
            counts = {}
            for element in data.get("elements", []):
                klass, _ = _classify_tags(element.get("tags", {}))
                if klass != "UNKNOWN":
                    counts[klass] = counts.get(klass, 0) + 1
            if not counts:
                return {"class": "UNKNOWN", "confidence": 0.0, "source": "OSM_OVERPASS_FALLBACK",
                        "evidence": "No mapped OSM land-cover polygons nearby."}
            klass = max(counts, key=counts.get)
            total = sum(counts.values())
            confidence = min(0.50 + 0.40 * counts[klass] / max(total, 1), 0.90)
            return {"class": klass, "confidence": round(confidence, 3),
                    "source": "OSM_OVERPASS_FALLBACK", "evidence": f"Nearby OSM context: {counts}"}
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
    return {"class": "UNKNOWN", "confidence": 0.0, "source": "UNAVAILABLE",
            "evidence": f"WorldCover and OSM land-cover lookup unavailable: {last_error}"}


def fetch_landcover(latitude, longitude):
    try:
        result = _worldcover_sample(latitude, longitude)
        if result:
            return result
    except Exception as exc:
        worldcover_error = str(exc)
    else:
        worldcover_error = "No valid WorldCover pixels returned."

    fallback = _fetch_osm_fallback(latitude, longitude)
    fallback["evidence"] = f"{fallback.get('evidence', '')} WorldCover fallback reason: {worldcover_error}"
    return fallback


def save_landcover(event_id, result):
    q = text("""
        INSERT INTO processed.event_land_cover
            (event_id, land_cover_class, land_cover_source, land_cover_confidence, evidence)
        VALUES (:event_id, :class, :source, :confidence, :evidence)
        ON CONFLICT (event_id) DO UPDATE SET
            land_cover_class = EXCLUDED.land_cover_class,
            land_cover_source = EXCLUDED.land_cover_source,
            land_cover_confidence = EXCLUDED.land_cover_confidence,
            evidence = EXCLUDED.evidence,
            updated_at = NOW()
    """)
    evidence = result.get("evidence")
    if not isinstance(evidence, str):
        import json
        evidence = json.dumps(evidence, sort_keys=True)
    with engine.begin() as conn:
        conn.execute(q, {"event_id": event_id, "class": result["class"],
                          "source": result["source"], "confidence": result["confidence"],
                          "evidence": evidence})


def process_recent_landcover(force=False):
    """Enrich every recent event, not an arbitrary 20-event subset.

    With force=True, existing OSM-derived records are re-sampled from the
    satellite product so old data is upgraded. Subsequent refreshes only query
    events that have no land-cover record yet.
    """
    if force:
        where = "e.last_detected_at >= CURRENT_TIMESTAMP - INTERVAL '168 hours'"
        params = {}
    else:
        where = "e.last_detected_at >= CURRENT_TIMESTAMP - INTERVAL '168 hours' AND lc.event_id IS NULL"
        params = {}
    q = text(f"""
        SELECT e.id, e.centroid_latitude AS latitude, e.centroid_longitude AS longitude
        FROM processed.thermal_events e
        LEFT JOIN processed.event_land_cover lc ON lc.event_id = e.id
        WHERE {where}
        ORDER BY e.last_detected_at DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, params).mappings().all()
    processed = 0
    for row in rows:
        if row["latitude"] is None or row["longitude"] is None:
            continue
        result = fetch_landcover(float(row["latitude"]), float(row["longitude"]))
        save_landcover(row["id"], result)
        processed += 1
    return processed


def process_missing_landcover():
    return process_recent_landcover(force=False)
