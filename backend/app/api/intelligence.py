from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.database import engine


router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["Event Intelligence"],
)


# ============================================================
# GET ALL EVENT INTELLIGENCE
# ============================================================

@router.get("")
def get_event_intelligence(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):
    """
    Return classified thermal events with intelligence scores.
    """

    query = text(
        """
        SELECT
            event_id,
            severity,
            confidence_score,
            classification,
            classification_confidence,
            class_probabilities,
            thermal_score,
            persistence_score,
            industrial_score,
            industrial_context,
            intelligence_reason,
            created_at,
            updated_at

        FROM processed.event_intelligence i
        JOIN processed.thermal_events e
            ON e.id = i.event_id
        WHERE e.last_detected_at >= (
            CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )

        ORDER BY event_id

        LIMIT :limit
        """
    )

    try:

        with engine.connect() as connection:

            rows = (
                connection.execute(
                    query,
                    {"limit": limit},
                )
                .mappings()
                .all()
            )

        intelligence = []

        for row in rows:

            intelligence.append(
                {
                    "event_id": row["event_id"],
                    "severity": row["severity"],
                    "confidence_score": (
                        float(row["confidence_score"])
                        if row["confidence_score"] is not None
                        else None
                    ),
                    "classification": row["classification"],
                    "classification_confidence": (
                        float(row["classification_confidence"])
                        if row["classification_confidence"] is not None
                        else None
                    ),
                    "class_probabilities": row["class_probabilities"],
                    "thermal_score": (
                        float(row["thermal_score"])
                        if row["thermal_score"] is not None
                        else None
                    ),
                    "persistence_score": (
                        float(row["persistence_score"])
                        if row["persistence_score"] is not None
                        else None
                    ),
                    "industrial_score": (
                        float(row["industrial_score"])
                        if row["industrial_score"] is not None
                        else None
                    ),
                    "industrial_context": (
                        row["industrial_context"]
                    ),
                    "intelligence_reason": (
                        row["intelligence_reason"]
                    ),
                    "created_at": (
                        row["created_at"].isoformat()
                        if row["created_at"]
                        else None
                    ),
                    "updated_at": (
                        row["updated_at"].isoformat()
                        if row["updated_at"]
                        else None
                    ),
                }
            )

        return {
            "count": len(intelligence),
            "intelligence": intelligence,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event intelligence.",
        ) from exc


# ============================================================
# GET INTELLIGENCE FOR ONE EVENT
# ============================================================

@router.get("/{event_id}")
def get_event_intelligence_by_id(
    event_id: int,
):
    """
    Return intelligence classification for one event.
    """

    query = text(
        """
        SELECT
            event_id,
            severity,
            confidence_score,
            classification,
            classification_confidence,
            class_probabilities,
            thermal_score,
            persistence_score,
            industrial_score,
            industrial_context,
            intelligence_reason,
            created_at,
            updated_at

        FROM processed.event_intelligence

        WHERE event_id = :event_id
        """
    )

    try:

        with engine.connect() as connection:

            row = (
                connection.execute(
                    query,
                    {"event_id": event_id},
                )
                .mappings()
                .one_or_none()
            )

        if row is None:

            raise HTTPException(
                status_code=404,
                detail="Event intelligence not found.",
            )

        return {
            "event_id": row["event_id"],
            "severity": row["severity"],
            "confidence_score": (
                float(row["confidence_score"])
                if row["confidence_score"] is not None
                else None
            ),
            "classification": row["classification"],
            "classification_confidence": (
                float(row["classification_confidence"])
                if row["classification_confidence"] is not None
                else None
            ),
            "class_probabilities": row["class_probabilities"],
            "thermal_score": (
                float(row["thermal_score"])
                if row["thermal_score"] is not None
                else None
            ),
            "persistence_score": (
                float(row["persistence_score"])
                if row["persistence_score"] is not None
                else None
            ),
            "industrial_score": (
                float(row["industrial_score"])
                if row["industrial_score"] is not None
                else None
            ),
            "industrial_context": (
                row["industrial_context"]
            ),
            "intelligence_reason": (
                row["intelligence_reason"]
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve event intelligence.",
        ) from exc