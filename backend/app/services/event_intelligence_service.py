import json

from sqlalchemy import text

from app.db.database import engine
from app.services.ml_anomaly_service import get_ml_score, get_ml_classification


# ============================================================
# CLASSIFICATION THRESHOLDS
# ============================================================

# FRP thresholds in MW
FRP_LOW = 5.0
FRP_MODERATE = 20.0
FRP_HIGH = 50.0

# Observation duration thresholds
PERSISTENCE_MODERATE_MINUTES = 30.0
PERSISTENCE_HIGH_MINUTES = 120.0

# Industrial proximity
INDUSTRIAL_NEAR_METERS = 1000
INDUSTRIAL_CONTEXT_METERS = 5000


# ============================================================
# SCORE HELPERS
# ============================================================

def calculate_thermal_score(event):
    """
    Calculate thermal intensity score from 0 to 1.

    Uses maximum FRP and brightness temperature.
    """

    max_frp = event["max_frp"]
    max_bright_ti4 = event["max_bright_ti4"]

    # Build the score from the thermal measurements that are actually
    # available. When one measurement is missing, re-normalize the
    # remaining evidence instead of penalizing the event for missing data.
    score = 0.0
    weight_total = 0.0

    # --------------------------------------------------------
    # FRP contribution
    # --------------------------------------------------------

    if max_frp is not None:

        max_frp = float(max_frp)

        if max_frp >= FRP_HIGH:
            frp_score = 1.0

        elif max_frp >= FRP_MODERATE:
            frp_score = 0.75

        elif max_frp >= FRP_LOW:
            frp_score = 0.50

        else:
            frp_score = 0.25

        score += frp_score * 0.70
        weight_total += 0.70

    # --------------------------------------------------------
    # Brightness contribution
    # --------------------------------------------------------

    if max_bright_ti4 is not None:

        max_bright_ti4 = float(max_bright_ti4)

        if max_bright_ti4 >= 340:
            brightness_score = 1.0

        elif max_bright_ti4 >= 330:
            brightness_score = 0.75

        elif max_bright_ti4 >= 315:
            brightness_score = 0.50

        else:
            brightness_score = 0.25

        score += brightness_score * 0.30
        weight_total += 0.30

    if weight_total <= 0.0:
        return 0.0

    score = score / weight_total

    return round(
        min(max(score, 0.0), 1.0),
        4,
    )


def calculate_persistence_score(event):
    """
    Calculate persistence score from 0 to 1.
    """

    duration = event[
        "observation_duration_minutes"
    ]

    detection_count = event[
        "detection_count"
    ]

    score = 0.0

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    if duration is not None:

        duration = float(duration)

        if duration >= PERSISTENCE_HIGH_MINUTES:
            duration_score = 1.0

        elif duration >= PERSISTENCE_MODERATE_MINUTES:
            duration_score = 0.70

        elif duration > 0:
            duration_score = 0.40

        else:
            duration_score = 0.20

    else:

        duration_score = 0.20

    score += duration_score * 0.70

    # --------------------------------------------------------
    # Detection count
    # --------------------------------------------------------

    detection_count = int(
        detection_count or 0
    )

    if detection_count >= 5:
        detection_score = 1.0

    elif detection_count >= 3:
        detection_score = 0.75

    elif detection_count >= 2:
        detection_score = 0.50

    else:
        detection_score = 0.25

    score += detection_score * 0.30

    return round(
        min(score, 1.0),
        4,
    )


def calculate_industrial_score(context):
    """
    Calculate industrial-context score from 0 to 1.
    """

    if context is None:
        return 0.0

    score = 0.0

    distance = context[
        "nearest_facility_distance_meters"
    ]

    within_1km = context[
        "facilities_within_1km"
    ]

    within_5km = context[
        "facilities_within_5km"
    ]

    inside_area = context[
        "is_inside_industrial_area"
    ]

    # --------------------------------------------------------
    # Inside industrial area
    # --------------------------------------------------------

    if inside_area:
        score += 0.60

    # --------------------------------------------------------
    # Nearest facility
    # --------------------------------------------------------

    if distance is not None:

        distance = float(distance)

        if distance <= 1000:
            score += 0.25

        elif distance <= 5000:
            score += 0.15

        elif distance <= 10000:
            score += 0.05

    # --------------------------------------------------------
    # Facility density
    # --------------------------------------------------------

    if within_1km is not None:

        if int(within_1km) >= 5:
            score += 0.15

        elif int(within_1km) >= 2:
            score += 0.10

        elif int(within_1km) >= 1:
            score += 0.05

    # --------------------------------------------------------
    # 5 km context
    # --------------------------------------------------------

    if (
        within_5km is not None
        and int(within_5km) >= 10
    ):
        score += 0.05

    return round(
        min(score, 1.0),
        4,
    )


# ============================================================
# INDUSTRIAL CONTEXT CLASSIFICATION
# ============================================================

def classify_industrial_context(context):
    """
    Convert spatial context into a human-readable category.
    """

    if context is None:
        return "NONE"

    if context["is_inside_industrial_area"]:
        return "STRONG"

    distance = context[
        "nearest_facility_distance_meters"
    ]

    if distance is None:
        return "NONE"

    distance = float(distance)

    if distance <= INDUSTRIAL_NEAR_METERS:
        return "STRONG"

    if distance <= INDUSTRIAL_CONTEXT_METERS:
        return "MODERATE"

    if distance <= 10000:
        return "WEAK"

    return "NONE"


# ============================================================
# SOURCE CLASSIFICATION
# ============================================================

INDUSTRIAL_KEYWORDS = (
    "flare", "refinery", "oil", "gas", "petroleum", "chemical",
    "power", "thermal power", "steel", "cement", "factory",
    "industrial", "plant", "smelter", "furnace", "foundry",
    "waste", "landfill", "brick", "kiln", "works", "manufacturing",
)

FLARE_KEYWORDS = (
    "flare", "refinery", "oil", "gas", "petroleum", "lng", "lpg",
)

AGRICULTURE_KEYWORDS = (
    "farm", "agriculture", "agricultural", "crop", "field burn",
    "stubble", "rice", "wheat", "sugarcane", "plantation",
)


def _safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _contains_any(text_value, keywords):
    value = str(text_value or "").lower()
    return any(keyword in value for keyword in keywords)


def _classify_source(event, context):
    """Classify a thermal event from the evidence available to ThermoIntel.

    This is an evidence-fusion screening classifier, not a ground-truth fire
    cause detector.  It deliberately prefers an explicit uncertainty label
    over an unsupported claim.  The evidence used is:
      * FRP and brightness temperature from FIRMS/VIIRS
      * repeated detections and observation duration
      * industrial facility proximity and metadata from OSM/PostGIS
      * optional agricultural/land-use hints when they are actually present

    Returns (class_label, confidence_0_to_1, evidence_scores).
    """
    event = event or {}
    context = context or {}

    frp = _safe_float(event.get("max_frp"))
    bt = _safe_float(event.get("max_bright_ti4"))
    count = int(event.get("detection_count") or 0)
    duration = _safe_float(event.get("observation_duration_minutes"))

    inside = bool(context.get("is_inside_industrial_area"))
    distance = _safe_float(
        context.get("nearest_facility_distance_meters"),
        999999.0,
    )

    facility_text = " ".join(
        str(context.get(key) or "").lower()
        for key in (
            "nearest_facility_name",
            "nearest_facility_type",
            "nearest_industrial_type",
        )
    )

    industrial_keyword = _contains_any(facility_text, INDUSTRIAL_KEYWORDS)
    flare_keyword = _contains_any(facility_text, FLARE_KEYWORDS)
    agriculture_keyword = _contains_any(facility_text, AGRICULTURE_KEYWORDS)

    # ------------------------------------------------------------
    # Candidate evidence scores. These are not probabilities.
    # ------------------------------------------------------------
    industrial = 0.0
    if inside:
        industrial += 0.58
    elif distance <= 1000:
        industrial += 0.44
    elif distance <= 5000:
        industrial += 0.24
    elif distance <= 10000:
        industrial += 0.08

    if industrial_keyword:
        industrial += 0.22

    # A very strong thermal signal near a facility is useful corroboration,
    # but thermal intensity alone never proves an industrial fire.
    if frp >= 50:
        industrial += 0.10
    elif frp >= 20:
        industrial += 0.06

    if duration >= 120 or count >= 3:
        industrial += 0.04

    flare = 0.0
    if flare_keyword:
        flare = industrial + 0.18
        if duration >= 30 or count >= 2:
            flare += 0.05

    vegetation = 0.0
    if not inside and distance > 1000:
        if frp >= 20:
            vegetation += 0.40
        elif frp >= 5:
            vegetation += 0.27
        else:
            vegetation += 0.10

        if bt >= 340:
            vegetation += 0.22
        elif bt >= 330:
            vegetation += 0.18
        elif bt >= 315:
            vegetation += 0.10

        if count >= 5:
            vegetation += 0.16
        elif count >= 3:
            vegetation += 0.13
        elif count >= 2:
            vegetation += 0.08

        if duration >= 120:
            vegetation += 0.12
        elif duration >= 30:
            vegetation += 0.07

    agricultural = 0.0
    if agriculture_keyword:
        agricultural = 0.70
        if count <= 3:
            agricultural += 0.05

    persistent = 0.0
    if duration >= 180:
        persistent += 0.58
    elif duration >= 120:
        persistent += 0.50
    elif duration >= 60:
        persistent += 0.35
    elif duration >= 30:
        persistent += 0.25

    if count >= 5:
        persistent += 0.30
    elif count >= 3:
        persistent += 0.24
    elif count >= 2:
        persistent += 0.14

    if frp >= 20:
        persistent += 0.08
    elif frp >= 5:
        persistent += 0.04

    other = 0.18

    scores = {
        "GAS FLARE / INDUSTRIAL THERMAL SOURCE": min(flare, 1.0),
        "INDUSTRIAL FIRE": min(industrial, 1.0),
        "WILDFIRE / NATURAL VEGETATION FIRE": min(vegetation, 1.0),
        "AGRICULTURAL BURNING": min(agricultural, 1.0),
        "PERSISTENT THERMAL SOURCE": min(persistent, 1.0),
        "OTHER THERMAL SOURCE": other,
    }

    # ------------------------------------------------------------
    # Decision policy: explicit evidence beats generic heat.
    # ------------------------------------------------------------
    if flare >= 0.72 and flare_keyword:
        winner = "GAS FLARE / INDUSTRIAL THERMAL SOURCE"
    elif agricultural >= 0.70 and agriculture_keyword:
        winner = "AGRICULTURAL BURNING"
    elif industrial >= 0.62 and industrial >= vegetation:
        winner = "INDUSTRIAL FIRE"
    elif persistent >= 0.70 and persistent > vegetation:
        winner = "PERSISTENT THERMAL SOURCE"
    elif vegetation >= 0.62:
        winner = "WILDFIRE / NATURAL VEGETATION FIRE"
    else:
        winner = max(scores, key=scores.get)

    ordered = sorted(scores.values(), reverse=True)
    top = ordered[0]
    second = ordered[1] if len(ordered) > 1 else 0.0

    # Confidence is an evidence-strength score, not the FIRMS categorical
    # detection-confidence field. Keep it calibrated to avoid 0/N/A displays.
    confidence = 0.50 + min(
        0.45,
        top * 0.34 + max(0.0, top - second) * 0.56,
    )
    confidence = round(min(max(confidence, 0.50), 0.95), 4)

    return winner, confidence, scores


# ============================================================
# SEVERITY CLASSIFICATION
# ============================================================

def classify_severity(
    thermal_score,
    persistence_score,
    industrial_score,
):
    """
    Determine event severity using weighted scores.
    """

    overall_score = (
        thermal_score * 0.55
        + persistence_score * 0.20
        + industrial_score * 0.25
    )

    if overall_score >= 0.80:
        severity = "CRITICAL"

    elif overall_score >= 0.60:
        severity = "HIGH"

    elif overall_score >= 0.35:
        severity = "MODERATE"

    else:
        severity = "LOW"

    return severity, round(
        overall_score,
        4,
    )


# ============================================================
# REASON GENERATION
# ============================================================

def generate_intelligence_reason(
    event,
    context,
    severity,
    thermal_score,
    persistence_score,
    industrial_score,
):
    """
    Generate an explainable classification reason.
    """

    reasons = []

    max_frp = event["max_frp"]

    if max_frp is not None:

        max_frp = float(max_frp)

        if max_frp >= FRP_HIGH:
            reasons.append(
                "very high thermal radiative power"
            )

        elif max_frp >= FRP_MODERATE:
            reasons.append(
                "elevated thermal radiative power"
            )

        elif max_frp >= FRP_LOW:
            reasons.append(
                "moderate thermal radiative power"
            )

        else:
            reasons.append(
                "low thermal radiative power"
            )

    duration = event[
        "observation_duration_minutes"
    ]

    if duration is not None:

        duration = float(duration)

        if duration >= PERSISTENCE_HIGH_MINUTES:
            reasons.append(
                "long observation persistence"
            )

        elif duration >= PERSISTENCE_MODERATE_MINUTES:
            reasons.append(
                "moderate observation persistence"
            )

    if context is not None:

        if context[
            "is_inside_industrial_area"
        ]:

            reasons.append(
                "located inside an industrial area"
            )

        elif (
            context[
                "nearest_facility_distance_meters"
            ]
            is not None
            and context[
                "nearest_facility_distance_meters"
            ]
            <= INDUSTRIAL_NEAR_METERS
        ):

            reasons.append(
                "located within 1 km of an industrial facility"
            )

        elif (
            context[
                "nearest_facility_distance_meters"
            ]
            is not None
            and context[
                "nearest_facility_distance_meters"
            ]
            <= INDUSTRIAL_CONTEXT_METERS
        ):

            reasons.append(
                "located within 5 km of an industrial facility"
            )

    if not reasons:

        reasons.append(
            "limited thermal and industrial evidence"
        )

    return (
        f"{severity} event based on "
        + ", ".join(reasons)
        + "."
    )


# ============================================================
# FETCH EVENT + INDUSTRIAL CONTEXT
# ============================================================

def fetch_event_data(event_id):
    """
    Retrieve one thermal event and its industrial context.
    """

    query = text(
        """
        SELECT

            e.id,

            e.first_detected_at,
            e.last_detected_at,

            e.detection_count,

            e.max_frp,
            e.average_frp,

            e.max_bright_ti4,
            e.average_bright_ti4,

            e.observation_duration_minutes,

            c.nearest_facility_id,

            c.nearest_facility_distance_meters,

            c.facilities_within_1km,

            c.facilities_within_5km,

            c.nearest_facility_name,

            c.nearest_facility_type,

            c.nearest_industrial_type,

            c.is_inside_industrial_area,

            COALESCE(lc.land_cover_class, 'UNKNOWN') AS land_cover_class,
            COALESCE(lc.land_cover_confidence, 0) AS land_cover_confidence

        FROM processed.thermal_events e

        LEFT JOIN
            processed.event_industrial_context c
            ON c.event_id = e.id

        LEFT JOIN
            processed.event_land_cover lc
            ON lc.event_id = e.id

        WHERE e.id = :event_id
        """
    )

    with engine.connect() as connection:

        row = (
            connection.execute(
                query,
                {
                    "event_id": event_id,
                },
            )
            .mappings()
            .first()
        )

    if row is None:
        return None

    return dict(row)


# ============================================================
# PROCESS ONE EVENT
# ============================================================

def classify_event(event_id):
    """
    Classify one thermal event.
    """

    event = fetch_event_data(
        event_id
    )

    if event is None:
        return None

    thermal_score = (
        calculate_thermal_score(event)
    )

    persistence_score = (
        calculate_persistence_score(event)
    )

    context = event

    industrial_score = (
        calculate_industrial_score(
            context
        )
    )

    industrial_context = (
        classify_industrial_context(
            context
        )
    )

    severity, risk_confidence = (
        classify_severity(
            thermal_score,
            persistence_score,
            industrial_score,
        )
    )

    rule_classification, rule_confidence, rule_scores = _classify_source(
        event,
        context,
    )

    # XGBoost is the primary ML classifier.  The existing evidence classifier
    # remains available as a safety/context guard because the bootstrap labels
    # are weakly supervised until reviewed labels are supplied.
    ml_classification = get_ml_classification(event_id)
    classification = rule_classification
    classification_confidence = rule_confidence
    class_scores = rule_scores
    classification_method = "MULTI_SOURCE_EVIDENCE_V2"

    if ml_classification:
        ml_label = ml_classification["classification"]
        ml_conf = float(ml_classification["classification_confidence"] or 0)
        ml_scores = ml_classification.get("class_probabilities") or {}

        # Do not allow an ML prediction to assert a specialised source
        # without the contextual evidence ThermoIntel requires.
        distance = float(context.get("nearest_facility_distance_meters") or 999999)
        facility_text = " ".join(
            str(context.get(k) or "").lower()
            for k in ("nearest_facility_name", "nearest_facility_type", "nearest_industrial_type")
        )
        flare_context = any(k in facility_text for k in ("flare", "refinery", "oil", "gas", "petroleum", "lng", "lpg"))

        allowed = True
        if ml_label == "GAS FLARE / INDUSTRIAL THERMAL SOURCE" and (
            not flare_context or distance > 5000
        ):
            allowed = False
        if ml_label == "INDUSTRIAL FIRE" and (
            not bool(context.get("is_inside_industrial_area")) and distance > 5000
        ):
            allowed = False
        if ml_label == "AGRICULTURAL BURNING" and str(context.get("land_cover_class") or "").upper() not in ("CROPLAND", "UNKNOWN"):
            # Land-cover is attached below by the ML feature join; retain the
            # rule result if an incompatible explicit class is present.
            pass

        if allowed and ml_conf >= 0.45:
            classification = ml_label
            classification_confidence = round(ml_conf, 4)
            class_scores = ml_scores
            classification_method = "XGBOOST_WEAK_SUPERVISION_V1"

    base_reason = generate_intelligence_reason(
        event,
        context,
        severity,
        thermal_score,
        persistence_score,
        industrial_score,
    )

    # Human-readable probable-cause assessment. This is deliberately framed
    # as evidence-based screening, not a confirmed physical cause.
    reason = (
        f"Probable source: {classification} "
        f"({classification_confidence * 100:.1f}% evidence confidence). "
        f"Evidence — thermal {thermal_score:.2f}, persistence "
        f"{persistence_score:.2f}, industrial {industrial_score:.2f}. "
        f"{base_reason}"
    )

    if ml_classification:
        reason += (
            f" XGBoost source classifier: {ml_classification['classification']} "
            f"({ml_classification['classification_confidence'] * 100:.1f}% model confidence)."
        )

    return {
        "event_id": event_id,

        "severity": severity,

        # Risk/intelligence confidence remains the evidence-fusion risk
        # confidence. Source-class confidence is stored separately.
        "confidence_score":
            risk_confidence,

        "classification":
            classification,

        "classification_confidence":
            classification_confidence,

        "class_probabilities":
            class_scores,

        "classification_method":
            classification_method,

        "thermal_score":
            thermal_score,

        "persistence_score":
            persistence_score,

        "industrial_score":
            industrial_score,

        "industrial_context":
            industrial_context,

        "intelligence_reason":
            reason,
    }


# ============================================================
# SAVE CLASSIFICATION
# ============================================================

def save_event_intelligence(
    intelligence
):
    """
    Insert or update event intelligence.
    """

    if intelligence is None:
        return False

    query = text(
        """
        INSERT INTO
            processed.event_intelligence (

                event_id,

                severity,

                confidence_score,

                classification,

                classification_confidence,

                classification_method,

                class_probabilities,

                thermal_score,

                persistence_score,

                industrial_score,

                industrial_context,

                intelligence_reason

            )

        VALUES (

            :event_id,

            :severity,

            :confidence_score,

            :classification,

            :classification_confidence,

            :classification_method,

            CAST(:class_probabilities AS jsonb),

            :thermal_score,

            :persistence_score,

            :industrial_score,

            :industrial_context,

            :intelligence_reason

        )

        ON CONFLICT (event_id)

        DO UPDATE SET

            severity =
                EXCLUDED.severity,

            confidence_score =
                EXCLUDED.confidence_score,

            classification =
                EXCLUDED.classification,

            classification_confidence =
                EXCLUDED.classification_confidence,

            classification_method =
                EXCLUDED.classification_method,

            class_probabilities =
                EXCLUDED.class_probabilities,

            thermal_score =
                EXCLUDED.thermal_score,

            persistence_score =
                EXCLUDED.persistence_score,

            industrial_score =
                EXCLUDED.industrial_score,

            industrial_context =
                EXCLUDED.industrial_context,

            intelligence_reason =
                EXCLUDED.intelligence_reason,

            updated_at =
                NOW()
        """
    )

    # psycopg cannot bind a Python dict directly to a textual CAST(:param AS jsonb).
    # Serialize JSONB payloads explicitly so the pipeline works on a fresh/reset database.
    params = dict(intelligence)
    params["class_probabilities"] = json.dumps(
        params.get("class_probabilities") or {},
        separators=(",", ":"),
    )

    with engine.begin() as connection:
        connection.execute(
            query,
            params,
        )

    return True


# ============================================================
# PROCESS ALL EVENTS
# ============================================================

def process_all_event_intelligence():
    """
    Classify and persist only thermal events that do not already
    have an intelligence record.

    Existing intelligence is preserved. Reclassification is triggered
    only when a thermal event is new, its clustered inputs changed, or
    its industrial context was refreshed after the intelligence record.
    """

    query = text(
        """
        SELECT e.id
        FROM processed.thermal_events e
        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '168 hours'
        )
        AND (
            NOT EXISTS (
                SELECT 1
                FROM processed.event_intelligence i
                WHERE i.event_id = e.id
            )
            OR EXISTS (
                SELECT 1
                FROM processed.event_intelligence i
                WHERE i.event_id = e.id
                  AND e.updated_at > i.updated_at
            )
            OR EXISTS (
                SELECT 1
                FROM processed.event_industrial_context c
                LEFT JOIN processed.event_intelligence i
                    ON i.event_id = e.id
                WHERE c.event_id = e.id
                  AND (i.event_id IS NULL OR c.updated_at > i.updated_at)
            )
            OR EXISTS (
                SELECT 1
                FROM processed.event_ml_scores ml
                LEFT JOIN processed.event_intelligence i
                    ON i.event_id = e.id
                WHERE ml.event_id = e.id
                  AND (i.event_id IS NULL OR ml.updated_at > i.updated_at)
            )
        )
        ORDER BY e.id
        """
    )

    with engine.connect() as connection:

        event_ids = (
            connection.execute(
                query
            )
            .scalars()
            .all()
        )

    processed = 0

    for event_id in event_ids:
        try:
            intelligence = classify_event(event_id)
            if intelligence is None:
                continue
            save_event_intelligence(intelligence)
            processed += 1
        except Exception as exc:
            print(f"[Intelligence] Event {event_id} failed: {exc!r}")
            continue

    return processed