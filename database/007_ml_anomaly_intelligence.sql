-- ML-assisted anomaly intelligence layer.
CREATE TABLE IF NOT EXISTS processed.event_ml_scores (
    event_id BIGINT PRIMARY KEY REFERENCES processed.thermal_events(id) ON DELETE CASCADE,
    model_name VARCHAR(120) NOT NULL,
    model_version VARCHAR(40) NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    normality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    trained_on_events INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS processed.ml_model_registry (
    model_name VARCHAR(120) PRIMARY KEY,
    model_version VARCHAR(40) NOT NULL,
    trained_on_events INTEGER NOT NULL DEFAULT 0,
    source_max_updated_at TIMESTAMPTZ,
    training_data_signature VARCHAR(160) NOT NULL DEFAULT 'UNKNOWN',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_event_ml_anomaly
ON processed.event_ml_scores(anomaly_score DESC);

ALTER TABLE processed.event_ml_scores
    ADD COLUMN IF NOT EXISTS predicted_class VARCHAR(100),
    ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS training_label_source VARCHAR(80) NOT NULL DEFAULT 'UNKNOWN',
    ADD COLUMN IF NOT EXISTS feature_version VARCHAR(80) NOT NULL DEFAULT 'UNKNOWN';

CREATE INDEX IF NOT EXISTS idx_event_ml_predicted_class
ON processed.event_ml_scores(predicted_class);
