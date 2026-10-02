"""Explainable multi-source thermal-source classifier for SIH26162.

This is a deterministic evidence-fusion classifier, not a trained ML model.
It uses NASA FIRMS thermal measurements, temporal persistence, OSM industrial
infrastructure and ESA WorldCover 10 m land-cover evidence. It never claims
that satellite context alone proves the physical cause of a thermal anomaly.
"""
from __future__ import annotations

import math
import json
from sqlalchemy import text
from app.db.database import engine

CLASSES = [
    "INDUSTRIAL FIRE",
    "GAS FLARE / INDUSTRIAL THERMAL SOURCE",
    "FOREST / VEGETATION FIRE",
    "AGRICULTURAL BURNING",
    "OTHER THERMAL SOURCE",
]

HYDROCARBON_TERMS = {
    "refinery", "oil", "gas", "petroleum", "petrochemical", "lng", "lpg",
    "fuel", "tank farm", "flare", "pipeline", "crude", "hydrocarbon",
}
INDUSTRIAL_TERMS = {
    "industrial", "factory", "plant", "steel", "cement", "chemical", "power",
    "manufacturing", "refinery", "petrochemical", "warehouse", "foundry",
}
VEGETATION_LAND = {"TREE_COVER", "SHRUBLAND", "GRASSLAND", "HERBACEOUS_WETLAND", "MANGROVES", "MOSS_LICHEN"}


def _norm(v):
    try:
        return max(0.0, min(float(v), 1.0))
    except (TypeError, ValueError):
        return 0.0


def _softmax(scores, temperature=1.0):
    vals = [v / temperature for v in scores.values()]
    m = max(vals)
    exps = {k: math.exp((v / temperature) - m) for k, v in scores.items()}
    total = sum(exps.values()) or 1.0
    return {k: round(exps[k] / total, 4) for k in scores}


def get_event_features(event_id):
    q = text("""
        SELECT e.id, e.max_frp, e.average_frp, e.max_bright_ti4,
               e.detection_count, e.observation_duration_minutes,
               e.centroid_latitude AS latitude, e.centroid_longitude AS longitude,
               COALESCE(c.nearest_facility_distance_meters, 999999) AS facility_distance,
               COALESCE(c.facilities_within_1km, 0) AS facilities_within_1km,
               COALESCE(c.facilities_within_5km, 0) AS facilities_within_5km,
               COALESCE(c.is_inside_industrial_area, FALSE) AS inside_industrial,
               COALESCE(c.nearest_facility_type, '') AS facility_type,
               COALESCE(c.nearest_industrial_type, '') AS industrial_type,
               COALESCE(lc.land_cover_class, 'UNKNOWN') AS land_cover_class,
               COALESCE(lc.land_cover_source, 'UNAVAILABLE') AS land_cover_source,
               COALESCE(lc.land_cover_confidence, 0) AS land_cover_confidence,
               COALESCE(lc.evidence, '') AS land_cover_evidence
        FROM processed.thermal_events e
        LEFT JOIN processed.event_industrial_context c ON c.event_id = e.id
        LEFT JOIN processed.event_land_cover lc ON lc.event_id = e.id
        WHERE e.id = :event_id
    """)
    with engine.connect() as conn:
        row = conn.execute(q, {"event_id": event_id}).mappings().first()
    return dict(row) if row else None


def _thermal_strength(frp, bt):
    frp_score = 0.0
    if frp >= 50: frp_score = 1.0
    elif frp >= 20: frp_score = 0.75
    elif frp >= 5: frp_score = 0.50
    elif frp > 0: frp_score = 0.25
    bt_score = 0.0
    if bt >= 340: bt_score = 1.0
    elif bt >= 330: bt_score = 0.75
    elif bt >= 315: bt_score = 0.50
    elif bt > 0: bt_score = 0.25
    if frp > 0 and bt > 0:
        return round(frp_score * .70 + bt_score * .30, 4)
    return round(frp_score or bt_score, 4)


def classify_source(event_id):
    e = get_event_features(event_id)
    if not e:
        return None

    frp = float(e.get("max_frp") or 0)
    bt = float(e.get("max_bright_ti4") or 0)
    duration = float(e.get("observation_duration_minutes") or 0)
    count = int(e.get("detection_count") or 0)
    distance = float(e.get("facility_distance") or 999999)
    inside = bool(e.get("inside_industrial"))
    facilities_1km = int(e.get("facilities_within_1km") or 0)
    facilities_5km = int(e.get("facilities_within_5km") or 0)
    land = str(e.get("land_cover_class") or "UNKNOWN").upper()
    land_conf = _norm(e.get("land_cover_confidence"))
    land_source = str(e.get("land_cover_source") or "UNAVAILABLE")
    facility_type = f"{e.get('facility_type','')} {e.get('industrial_type','')}".lower()

    thermal = _thermal_strength(frp, bt)
    persistence = min((duration / 120.0) * 0.7 + min(count / 5.0, 1.0) * 0.3, 1.0)

    industrial = 0.0
    if inside: industrial += .55
    if distance <= 500: industrial += .30
    elif distance <= 1000: industrial += .25
    elif distance <= 3000: industrial += .18
    elif distance <= 5000: industrial += .12
    elif distance <= 10000: industrial += .05
    if facilities_1km >= 5: industrial += .15
    elif facilities_1km >= 2: industrial += .10
    elif facilities_1km >= 1: industrial += .05
    if facilities_5km >= 10: industrial += .05
    if any(term in facility_type for term in INDUSTRIAL_TERMS): industrial += .08
    industrial = min(industrial, 1.0)

    hydrocarbon = any(term in facility_type for term in HYDROCARBON_TERMS)
    flare_evidence = min(1.0, industrial * .75 + (0.25 if hydrocarbon and distance <= 3000 else 0.0))

    vegetation = land_conf if land in VEGETATION_LAND else 0.0
    agriculture = land_conf if land == "CROPLAND" else 0.0
    built = land_conf if land == "BUILT_UP" else 0.0

    # Source-specific evidence scores. These are intentionally asymmetric:
    # industrial/flare requires infrastructure evidence; agriculture requires
    # cropland evidence; vegetation requires a vegetation land-cover signal.
    scores = {
        "INDUSTRIAL FIRE": 0.05 + 3.50 * industrial + 0.25 * built + 0.25 * thermal + 0.15 * persistence,
        "GAS FLARE / INDUSTRIAL THERMAL SOURCE": 0.02 + 4.20 * flare_evidence + 0.35 * thermal + 0.20 * persistence,
        "FOREST / VEGETATION FIRE": 0.05 + 3.00 * vegetation + 0.55 * persistence + 0.35 * thermal - 0.90 * industrial,
        "AGRICULTURAL BURNING": 0.05 + 3.25 * agriculture + 0.35 * thermal + 0.20 * persistence - 0.90 * industrial,
        "OTHER THERMAL SOURCE": 0.12 + 0.80 * (1 - max(industrial, vegetation, agriculture)) + 0.15 * (1 - thermal),
    }

    # Gas flaring is a special industrial subtype and should only win when a
    # hydrocarbon-related facility is actually nearby.
    if not hydrocarbon or distance > 5000:
        scores["GAS FLARE / INDUSTRIAL THERMAL SOURCE"] -= 1.50
    if industrial < 0.25:
        scores["INDUSTRIAL FIRE"] -= 1.50

    # If there is no reliable contextual evidence, keep the result as Other
    # rather than inventing a cause. This is an uncertainty guard, not a UI fallback.
    if land == "UNKNOWN" and industrial < 0.25:
        scores["OTHER THERMAL SOURCE"] += 1.00

    probabilities = _softmax(scores, temperature=0.85)
    classification = max(probabilities, key=probabilities.get)
    confidence = probabilities[classification]

    evidence = {
        "thermal_strength": round(thermal, 4),
        "persistence_strength": round(persistence, 4),
        "industrial_evidence": round(industrial, 4),
        "flare_evidence": round(flare_evidence, 4),
        "land_cover_class": land,
        "land_cover_confidence": land_conf,
        "land_cover_source": land_source,
        "nearest_facility_distance_m": None if distance >= 999999 else round(distance, 1),
        "facilities_within_1km": facilities_1km,
        "facilities_within_5km": facilities_5km,
        "hydrocarbon_facility_signal": hydrocarbon,
    }

    return {
        "classification": classification,
        "classification_confidence": round(confidence, 4),
        "class_probabilities": probabilities,
        "method": "MULTI_SOURCE_EVIDENCE_V2",
        "land_cover_class": land,
        "land_cover_confidence": land_conf,
        "land_cover_source": land_source,
        "land_cover_evidence": e.get("land_cover_evidence") or "",
        "evidence": evidence,
    }
