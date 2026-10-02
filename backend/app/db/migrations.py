from pathlib import Path
from sqlalchemy import text
from app.db.database import engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "database"


def ensure_schema():
    """Apply lightweight idempotent migrations required by the running app.

    Docker's init directory only runs on a brand-new PostgreSQL volume, so this
    function also upgrades an existing ThermoIntel database safely.
    """
    statements = [
        "CREATE SCHEMA IF NOT EXISTS processed",
        """CREATE TABLE IF NOT EXISTS processed.event_land_cover (
            event_id BIGINT PRIMARY KEY REFERENCES processed.thermal_events(id) ON DELETE CASCADE,
            land_cover_class VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN',
            land_cover_source VARCHAR(80) NOT NULL DEFAULT 'UNAVAILABLE',
            land_cover_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            evidence TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS classification VARCHAR(50) NOT NULL DEFAULT 'OTHER THERMAL SOURCE'",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS classification_method VARCHAR(80) NOT NULL DEFAULT 'MULTI_SOURCE_EVIDENCE_V2'",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS classification_evidence JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS land_cover_class VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN'",
        "ALTER TABLE processed.event_intelligence ADD COLUMN IF NOT EXISTS land_cover_confidence DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE processed.event_risk_scores ADD COLUMN IF NOT EXISTS classification VARCHAR(50) NOT NULL DEFAULT 'OTHER THERMAL SOURCE'",
        "ALTER TABLE processed.event_risk_scores ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE processed.event_risk_scores ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE processed.event_risk_scores ADD COLUMN IF NOT EXISTS classification_evidence JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE processed.event_risk_scores ADD COLUMN IF NOT EXISTS land_cover_class VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN'",
        """CREATE TABLE IF NOT EXISTS processed.event_ml_scores (
            event_id BIGINT PRIMARY KEY REFERENCES processed.thermal_events(id) ON DELETE CASCADE,
            model_name VARCHAR(120) NOT NULL,
            model_version VARCHAR(40) NOT NULL,
            anomaly_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            normality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            trained_on_events INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS processed.ml_model_registry (
            model_name VARCHAR(120) PRIMARY KEY,
            model_version VARCHAR(40) NOT NULL,
            trained_on_events INTEGER NOT NULL DEFAULT 0,
            source_max_updated_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        "ALTER TABLE processed.event_ml_scores ADD COLUMN IF NOT EXISTS predicted_class VARCHAR(100)",
        "ALTER TABLE processed.event_ml_scores ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE processed.event_ml_scores ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE processed.event_ml_scores ADD COLUMN IF NOT EXISTS training_label_source VARCHAR(80) NOT NULL DEFAULT 'UNKNOWN'",
        "ALTER TABLE processed.event_ml_scores ADD COLUMN IF NOT EXISTS feature_version VARCHAR(80) NOT NULL DEFAULT 'UNKNOWN'",
        "ALTER TABLE processed.ml_model_registry ADD COLUMN IF NOT EXISTS training_data_signature VARCHAR(160) NOT NULL DEFAULT 'UNKNOWN'",
        "CREATE INDEX IF NOT EXISTS idx_event_ml_predicted_class ON processed.event_ml_scores(predicted_class)",
        "CREATE INDEX IF NOT EXISTS idx_event_ml_anomaly ON processed.event_ml_scores(anomaly_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_event_land_cover_class ON processed.event_land_cover(land_cover_class)",
        "CREATE INDEX IF NOT EXISTS idx_event_intelligence_classification ON processed.event_intelligence(classification)",
        "CREATE INDEX IF NOT EXISTS idx_event_risk_classification ON processed.event_risk_scores(classification)",
        """UPDATE processed.event_intelligence i
           SET classification = r.classification,
               classification_confidence = r.classification_confidence,
               classification_method = COALESCE(i.classification_method, 'MULTI_SOURCE_EVIDENCE_V2'),
               class_probabilities = CASE
                   WHEN i.class_probabilities IS NULL OR i.class_probabilities = '{}'::jsonb
                   THEN COALESCE(r.class_probabilities, '{}'::jsonb)
                   ELSE i.class_probabilities
               END,
               classification_evidence = CASE
                   WHEN i.classification_evidence IS NULL OR i.classification_evidence = '{}'::jsonb
                   THEN COALESCE(r.classification_evidence, '{}'::jsonb)
                   ELSE i.classification_evidence
               END,
               land_cover_class = CASE
                   WHEN i.land_cover_class IS NULL OR i.land_cover_class = 'UNKNOWN'
                   THEN COALESCE(r.land_cover_class, i.land_cover_class, 'UNKNOWN')
                   ELSE i.land_cover_class
               END,
               updated_at = NOW()
         FROM processed.event_risk_scores r
         WHERE r.event_id = i.event_id
           AND (
               i.classification IS NULL
               OR UPPER(TRIM(i.classification)) IN ('THERMAL ANOMALY','OTHER THERMAL ANOMALY','PENDING CLASSIFICATION')
               OR COALESCE(i.classification_confidence,0) <= 0
           )""",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
