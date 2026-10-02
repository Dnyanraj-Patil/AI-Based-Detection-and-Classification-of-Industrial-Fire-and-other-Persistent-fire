from sqlalchemy import text

from app.db.database import engine
from app.services.event_intelligence_service import (
    classify_event,
)


# ============================================================
# EVIDENCE FUSION WEIGHTS
# ============================================================

THERMAL_WEIGHT = 0.45
PERSISTENCE_WEIGHT = 0.25
INDUSTRIAL_WEIGHT = 0.30


# ============================================================
# SCORE VALIDATION
# ============================================================

def normalize_score(value):
    """
    Ensure an evidence score is safely represented
    between 0 and 1.
    """

    if value is None:
        return 0.0

    value = float(value)

    if value < 0:
        return 0.0

    if value > 1:
        return 1.0

    return value


# ============================================================
# CALCULATE EVIDENCE SCORE
# ============================================================

def calculate_evidence_score(
    thermal_score,
    persistence_score,
    industrial_score,
):
    """
    Combine individual evidence components into one
    normalized evidence score.

    Current model:

        Thermal       = 45%
        Persistence   = 25%
        Industrial    = 30%

    Returns a value between 0 and 1.
    """

    thermal_score = normalize_score(
        thermal_score
    )

    persistence_score = normalize_score(
        persistence_score
    )

    industrial_score = normalize_score(
        industrial_score
    )

    evidence_score = (

        thermal_score
        * THERMAL_WEIGHT

        +

        persistence_score
        * PERSISTENCE_WEIGHT

        +

        industrial_score
        * INDUSTRIAL_WEIGHT
    )

    return round(
        min(
            max(evidence_score, 0.0),
            1.0,
        ),
        4,
    )


# ============================================================
# RISK SCORE
# ============================================================

def calculate_risk_score(
    evidence_score,
    confidence_score,
):
    """
    Combine evidence strength and classifier confidence.

    Evidence contributes 70%.
    Classifier confidence contributes 30%.
    """

    evidence_score = normalize_score(
        evidence_score
    )

    confidence_score = normalize_score(
        confidence_score
    )

    risk_score = (
        evidence_score * 0.70
        +
        confidence_score * 0.30
    )

    return round(
        min(
            max(risk_score, 0.0),
            1.0,
        ),
        4,
    )


# ============================================================
# RISK BAND
# ============================================================

def determine_risk_band(risk_score):
    """
    Convert numerical risk score into an operational
    risk band.

        0.00 - 0.29 -> LOW
        0.30 - 0.49 -> MODERATE
        0.50 - 0.69 -> HIGH
        0.70 - 1.00 -> CRITICAL
    """

    risk_score = normalize_score(
        risk_score
    )

    if risk_score >= 0.70:
        return "CRITICAL"

    if risk_score >= 0.50:
        return "HIGH"

    if risk_score >= 0.30:
        return "MODERATE"

    return "LOW"


# ============================================================
# BUILD EVENT RISK
# ============================================================

def calculate_event_risk(event_id):
    """
    Calculate evidence fusion and risk information
    for one thermal event.

    The existing event intelligence classifier remains
    the source of thermal/persistence/industrial evidence
    and confidence.
    """

    intelligence = classify_event(
        event_id
    )

    if intelligence is None:
        return None

    thermal_score = normalize_score(
        intelligence.get(
            "thermal_score"
        )
    )

    persistence_score = normalize_score(
        intelligence.get(
            "persistence_score"
        )
    )

    industrial_score = normalize_score(
        intelligence.get(
            "industrial_score"
        )
    )

    confidence_score = normalize_score(
        intelligence.get(
            "confidence_score"
        )
    )

    evidence_score = (
        calculate_evidence_score(
            thermal_score,
            persistence_score,
            industrial_score,
        )
    )

    risk_score = (
        calculate_risk_score(
            evidence_score,
            confidence_score,
        )
    )

    risk_band = determine_risk_band(
        risk_score
    )

    return {
        "event_id": event_id,

        "thermal_score":
            thermal_score,

        "persistence_score":
            persistence_score,

        "industrial_score":
            industrial_score,

        "evidence_score":
            evidence_score,

        "risk_score":
            risk_score,

        "severity":
            intelligence.get(
                "severity"
            ),

        "confidence_score":
            confidence_score,

        "classification": intelligence.get("classification") or "OTHER THERMAL SOURCE",
        "classification_confidence": normalize_score(intelligence.get("classification_confidence")),
        "class_probabilities": intelligence.get("class_probabilities") or {},

        "industrial_context":
            intelligence.get(
                "industrial_context"
            ),

        "intelligence_reason":
            intelligence.get(
                "intelligence_reason"
            ),

        "risk_band":
            risk_band,
    }


# ============================================================
# SAVE EVENT RISK
# ============================================================

def save_event_risk(risk):
    """
    Insert or update the risk record for one event.
    """

    if risk is None:
        return False

    query = text(
        """
        INSERT INTO processed.event_risk_scores (

            event_id,

            thermal_score,

            persistence_score,

            industrial_score,

            evidence_score,

            risk_score,

            severity,

            confidence_score,

            classification,
            classification_confidence,
            class_probabilities,

            industrial_context,

            intelligence_reason,

            risk_band

        )

        VALUES (

            :event_id,

            :thermal_score,

            :persistence_score,

            :industrial_score,

            :evidence_score,

            :risk_score,

            :severity,

            :confidence_score,

            :classification,
            :classification_confidence,
            CAST(:class_probabilities AS jsonb),

            :industrial_context,

            :intelligence_reason,

            :risk_band
        )

        ON CONFLICT (event_id)

        DO UPDATE SET

            thermal_score =
                EXCLUDED.thermal_score,

            persistence_score =
                EXCLUDED.persistence_score,

            industrial_score =
                EXCLUDED.industrial_score,

            evidence_score =
                EXCLUDED.evidence_score,

            risk_score =
                EXCLUDED.risk_score,

            severity =
                EXCLUDED.severity,

            confidence_score =
                EXCLUDED.confidence_score,

            classification = EXCLUDED.classification,
            classification_confidence = EXCLUDED.classification_confidence,
            class_probabilities = EXCLUDED.class_probabilities,

            industrial_context =
                EXCLUDED.industrial_context,

            intelligence_reason =
                EXCLUDED.intelligence_reason,

            risk_band =
                EXCLUDED.risk_band,

            updated_at =
                NOW()
        """
    )

    with engine.begin() as connection:

        connection.execute(
            query,
            {
                "event_id":
                    risk["event_id"],

                "thermal_score":
                    risk["thermal_score"],

                "persistence_score":
                    risk["persistence_score"],

                "industrial_score":
                    risk["industrial_score"],

                "evidence_score":
                    risk["evidence_score"],

                "risk_score":
                    risk["risk_score"],

                "severity":
                    risk["severity"],

                "confidence_score": risk["confidence_score"],
                "classification": risk["classification"],
                "classification_confidence": risk["classification_confidence"],
                "class_probabilities": __import__("json").dumps(risk["class_probabilities"]),

                "industrial_context":
                    risk["industrial_context"],

                "intelligence_reason":
                    risk["intelligence_reason"],

                "risk_band":
                    risk["risk_band"],
            },
        )

    return True


# ============================================================
# PROCESS ONE EVENT
# ============================================================

def process_event_risk(event_id):

    risk = calculate_event_risk(
        event_id
    )

    if risk is None:
        return None

    save_event_risk(
        risk
    )

    return risk


# ============================================================
# PROCESS ALL EVENTS
# ============================================================

def process_all_event_risk():
    """
    Calculate and persist risk only for thermal events that do not
    already have a risk record.

    Existing risk intelligence is preserved. Recalculation is triggered
    only when a thermal event changed, its intelligence changed, or the
    risk record is missing.
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
                FROM processed.event_risk_scores r
                WHERE r.event_id = e.id
            )
            OR EXISTS (
                SELECT 1
                FROM processed.event_risk_scores r
                WHERE r.event_id = e.id
                  AND e.updated_at > r.updated_at
            )
            OR EXISTS (
                SELECT 1
                FROM processed.event_intelligence i
                LEFT JOIN processed.event_risk_scores r
                    ON r.event_id = e.id
                WHERE i.event_id = e.id
                  AND (r.event_id IS NULL OR i.updated_at > r.updated_at)
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

    results = []

    for event_id in event_ids:
        try:
            risk = process_event_risk(event_id)
            if risk is not None:
                results.append(risk)
        except Exception as exc:
            print(f"[Risk] Event {event_id} failed: {exc!r}")
            continue

    return results