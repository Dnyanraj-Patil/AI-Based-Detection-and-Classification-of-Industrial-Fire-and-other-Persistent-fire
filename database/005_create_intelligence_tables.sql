CREATE TABLE IF NOT EXISTS processed.event_industrial_context (
    event_id BIGINT PRIMARY KEY
        REFERENCES processed.thermal_events(id)
        ON DELETE CASCADE,

    nearest_facility_id BIGINT
        REFERENCES raw.industrial_facilities(id)
        ON DELETE SET NULL,

    nearest_facility_distance_meters DOUBLE PRECISION,
    facilities_within_1km INTEGER NOT NULL DEFAULT 0,
    facilities_within_5km INTEGER NOT NULL DEFAULT 0,

    nearest_facility_name TEXT,
    nearest_facility_type VARCHAR(100),
    nearest_industrial_type VARCHAR(100),

    is_inside_industrial_area BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_context_facility
ON processed.event_industrial_context(nearest_facility_id);


CREATE TABLE IF NOT EXISTS processed.event_intelligence (
    event_id BIGINT PRIMARY KEY
        REFERENCES processed.thermal_events(id)
        ON DELETE CASCADE,

    severity VARCHAR(20) NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    classification VARCHAR(100),
    classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    thermal_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    persistence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    industrial_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    industrial_context VARCHAR(20) NOT NULL DEFAULT 'NONE',
    intelligence_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_intelligence_severity
ON processed.event_intelligence(severity);


CREATE TABLE IF NOT EXISTS processed.event_risk_scores (
    event_id BIGINT PRIMARY KEY
        REFERENCES processed.thermal_events(id)
        ON DELETE CASCADE,

    thermal_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    persistence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    industrial_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    evidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,

    severity VARCHAR(20) NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    industrial_context VARCHAR(20) NOT NULL DEFAULT 'NONE',
    intelligence_reason TEXT,
    risk_band VARCHAR(20) NOT NULL DEFAULT 'LOW',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_risk_score
ON processed.event_risk_scores(risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_event_risk_band
ON processed.event_risk_scores(risk_band);


-- Upgrade existing ThermoIntel installations.
ALTER TABLE IF EXISTS processed.event_intelligence
    ADD COLUMN IF NOT EXISTS classification VARCHAR(100);

ALTER TABLE IF EXISTS processed.event_intelligence
    ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS processed.event_intelligence
    ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Backfill an immediately usable classification/confidence from the
-- evidence already present in existing records. The full Python classifier
-- will refine these values on the next intelligence pipeline run.
UPDATE processed.event_intelligence i
SET classification = CASE
    WHEN COALESCE(i.industrial_score, 0) >= 0.62
        THEN 'INDUSTRIAL FIRE'
    WHEN COALESCE(i.thermal_score, 0) >= 0.50
         AND COALESCE(i.persistence_score, 0) >= 0.40
        THEN 'WILDFIRE / VEGETATION FIRE'
    ELSE 'OTHER THERMAL SOURCE'
END,
classification_confidence = CASE
    WHEN COALESCE(i.industrial_score, 0) >= 0.62
        THEN LEAST(0.90, GREATEST(0.55,
             0.50 + COALESCE(i.industrial_score, 0) * 0.35))
    WHEN COALESCE(i.thermal_score, 0) >= 0.50
         AND COALESCE(i.persistence_score, 0) >= 0.40
        THEN LEAST(0.90, GREATEST(0.55,
             0.50 + COALESCE(i.thermal_score, 0) * 0.30
                  + COALESCE(i.persistence_score, 0) * 0.20))
    ELSE 0.55
END
WHERE classification IS NULL
   OR classification_confidence <= 0;
