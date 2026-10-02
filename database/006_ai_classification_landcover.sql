CREATE TABLE IF NOT EXISTS processed.event_land_cover (
    event_id BIGINT PRIMARY KEY REFERENCES processed.thermal_events(id) ON DELETE CASCADE,
    land_cover_class VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN',
    land_cover_source VARCHAR(80) NOT NULL DEFAULT 'UNAVAILABLE',
    land_cover_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    evidence TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_land_cover_class
ON processed.event_land_cover(land_cover_class);

ALTER TABLE processed.event_intelligence
    ADD COLUMN IF NOT EXISTS classification VARCHAR(50) NOT NULL DEFAULT 'OTHER THERMAL SOURCE',
    ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS classification_method VARCHAR(80) NOT NULL DEFAULT 'MULTI_SOURCE_EVIDENCE_V2',
    ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS classification_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS land_cover_class VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN',
    ADD COLUMN IF NOT EXISTS land_cover_confidence DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE processed.event_risk_scores
    ADD COLUMN IF NOT EXISTS classification VARCHAR(50) NOT NULL DEFAULT 'OTHER THERMAL SOURCE',
    ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS classification_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS land_cover_class VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN';

CREATE INDEX IF NOT EXISTS idx_event_intelligence_classification
ON processed.event_intelligence(classification);

CREATE INDEX IF NOT EXISTS idx_event_risk_classification
ON processed.event_risk_scores(classification);
